"""GUI controller: UIイベントからユースケース呼び出しを仲介する。"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Callable

from app.data.file_cache import FileCache
from app.data.kabutan_repository import KabutanForecastRepository
from app.data.market_data_provider import fetch_yfinance_snapshot
from app.data.watchlist_repository import fetch_watchlist_entries
from app.domain.usecases.kabutan_html_dir import ResolveKabutanHtmlDirUseCase, ResolvedKabutanHtmlDir
from app.domain.usecases.watchlist_path import ResolveWatchlistPathUseCase, ResolvedWatchlistPath
from app.domain.usecases.kabutan_forecast import FetchKabutanForecastUseCase
from app.domain.usecases.fundamental_analysis import FundamentalAnalysisService
from app.domain.usecases.fundamental_summary import FundamentalSummaryService
from app.domain.builders.fundamental_summary import build_fundamental_summary_markdown
from app.domain.builders.institutional_summary import build_institutional_summary_text
from app.domain.builders.technical_output import build_technical_output
from app.domain.policies.cf_scoring import calculate_cf_score
from app.domain.policies.institutional_summary import build_institutional_summary
from app.domain.usecases.technical_analysis import TechnicalAnalysisService
from app.presenters import build_fundamental_output

FUNDAMENTAL_SUMMARY_FILENAME_PREFIX = "fundamental_summery"


def build_fundamental_summary_filename(*, today: date | None = None) -> str:
    target_date = today or date.today()
    return f"{FUNDAMENTAL_SUMMARY_FILENAME_PREFIX}-{target_date.isoformat()}.md"


def build_default_fundamental_service(file_cache: FileCache) -> FundamentalAnalysisService:
    kabutan_repository = KabutanForecastRepository(file_cache=file_cache)
    return FundamentalAnalysisService(
        file_cache=file_cache,
        fetch_market_snapshot=fetch_yfinance_snapshot,
        fetch_kabutan_forecast_usecase=FetchKabutanForecastUseCase(
            repository=kabutan_repository
        ),
    )


def build_default_technical_service(file_cache: FileCache) -> TechnicalAnalysisService:
    return TechnicalAnalysisService(file_cache=file_cache)


class FundamentalGuiController:
    """GUI層コントローラー: 表示以外のオーケストレーションを担当。"""

    def __init__(
        self,
        file_cache: FileCache | None = None,
        build_fundamental_service: Callable[[FileCache], FundamentalAnalysisService] | None = None,
        build_technical_service: Callable[[FileCache], TechnicalAnalysisService] | None = None,
    ):
        self.file_cache = file_cache or FileCache()
        self.resolve_kabutan_html_dir_usecase = ResolveKabutanHtmlDirUseCase()
        self.resolve_watchlist_path_usecase = ResolveWatchlistPathUseCase()
        self.build_fundamental_service = build_fundamental_service or build_default_fundamental_service
        self.build_technical_service = build_technical_service or build_default_technical_service

    def fetch_resolved_kabutan_html_dir(self) -> ResolvedKabutanHtmlDir:
        cached_dir = self.file_cache.fetch_kabutan_html_dir_cache()
        return self.resolve_kabutan_html_dir_usecase.fetch_resolved_kabutan_html_dir(cached_dir)

    def save_kabutan_html_dir_cache(self, path: Path) -> None:
        self.file_cache.save_kabutan_html_dir_cache(path)

    def fetch_resolved_watchlist_path(self) -> ResolvedWatchlistPath:
        cached_path = self.file_cache.fetch_watchlist_path_cache()
        return self.resolve_watchlist_path_usecase.fetch_resolved_watchlist_path(cached_path)

    def save_watchlist_path_cache(self, path: Path) -> None:
        self.file_cache.save_watchlist_path_cache(path)

    def fetch_output_cache_for_today(self) -> dict[str, str]:
        return self.file_cache.fetch_output_cache_for_today()

    def save_output_cache_for_today(self, output_cache: dict[str, str]) -> None:
        self.file_cache.save_output_cache_for_today(output_cache)

    def fetch_watchlist_entries(self, path: Path) -> list[tuple[str, str]]:
        return fetch_watchlist_entries(path)

    def fetch_analysis_output(
        self,
        *,
        name: str,
        code4: str,
        output_cache: dict[str, str],
        output_cache_key: str,
        kabutan_html_dir: Path | None = None,
    ) -> str:
        cached_output = output_cache.get(output_cache_key)
        if cached_output is not None:
            return cached_output

        service = self.build_fundamental_service(self.file_cache)
        output = service.build_analysis_output(
            name,
            code4,
            build_output_fn=build_fundamental_output,
            kabutan_html_dir=kabutan_html_dir,
        )
        output_cache[output_cache_key] = output
        return output

    def build_and_save_fundamental_summary(
        self,
        *,
        watchlist_entries: list[tuple[str, str]],
        output_dir: Path,
        kabutan_html_dir: Path | None = None,
        today: date | None = None,
    ) -> Path:
        service = FundamentalSummaryService(self.build_fundamental_service(self.file_cache))
        table = service.build_summary_table(watchlist_entries, kabutan_html_dir=kabutan_html_dir)
        markdown = build_fundamental_summary_markdown(table)
        output_path = output_dir / build_fundamental_summary_filename(today=today)
        output_path.write_text(markdown, encoding="utf-8")
        return output_path

    def fetch_technical_output(
        self,
        *,
        name: str,
        code4: str,
    ) -> str:
        service = self.build_technical_service(self.file_cache)
        result = service.build_analysis_result(name=name, code4=code4)
        return build_technical_output(result)

    def fetch_institutional_summary_text(
        self,
        *,
        name: str,
        code4: str,
        kabutan_html_dir: Path | None = None,
    ) -> str:
        technical_service = self.build_technical_service(self.file_cache)
        technical_result = technical_service.build_analysis_result(name=name, code4=code4)

        fundamental_service = self.build_fundamental_service(self.file_cache)
        price_snapshot = fundamental_service.fetch_price_snapshot(code4)
        cf_scoring_input = None
        if kabutan_html_dir is not None:
            kabutan_fetch_result = fundamental_service.fetch_kabutan_forecast_pair(code4, html_dir=kabutan_html_dir)
            financial_metric_rows = fundamental_service.build_financial_metric_rows(
                price=price_snapshot.get("price"),
                forecast_pair=kabutan_fetch_result.pair,
                balance_sheet_rows=kabutan_fetch_result.balance_sheet_rows,
            )
            cf_scoring_input = fundamental_service.build_cf_scoring_input(
                code4=code4,
                as_of=fundamental_service.resolve_cf_scoring_as_of(
                    price_snapshot=price_snapshot,
                    forecast_pair=kabutan_fetch_result.pair,
                ),
                price=price_snapshot.get("price"),
                market_per=price_snapshot.get("per"),
                market_cap=price_snapshot.get("market_cap"),
                forecast_pair=kabutan_fetch_result.pair,
                cashflow_rows=kabutan_fetch_result.cashflow_rows,
                financial_metric_rows=financial_metric_rows,
            )
        scoring_result = calculate_cf_score(cf_scoring_input) if cf_scoring_input is not None else None
        summary = build_institutional_summary(
            market_cap_yen=price_snapshot.get("market_cap") if isinstance(price_snapshot.get("market_cap"), (int, float)) else None,
            close=technical_result.snapshot.price.close,
            volume=technical_result.snapshot.price.volume,
            volume_avg20=technical_result.snapshot.price.volume_avg20,
            roic_pct=cf_scoring_input.roic if cf_scoring_input is not None else None,
            eps_cagr_pct=cf_scoring_input.eps_cagr_3y if cf_scoring_input is not None else None,
            fundamental_score=scoring_result.total.total_points if scoring_result is not None else None,
            fundamental_rank=scoring_result.total.judgement if scoring_result is not None else None,
            latest=technical_result.snapshot.price.latest,
            vwap=technical_result.vwap_snapshot.get("vwap") if isinstance(technical_result.vwap_snapshot.get("vwap"), (int, float)) else None,
            ma5=technical_result.snapshot.moving_average.ma5,
            ma25=technical_result.snapshot.moving_average.ma25,
            vwap_is_daily_reference=technical_result.vwap_snapshot.get("vwap_source") == "日足参考値",
        )
        return build_institutional_summary_text(summary)


__all__ = [
    "FUNDAMENTAL_SUMMARY_FILENAME_PREFIX",
    "FundamentalGuiController",
    "build_fundamental_summary_filename",
    "build_default_technical_service",
]
