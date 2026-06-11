"""GUI controller: UIイベントからユースケース呼び出しを仲介する。"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Callable

from app.data.file_cache import FileCache
from app.data.kabutan_repository import KabutanForecastRepository
from app.data.market_data_provider import fetch_yfinance_analyst_estimates, fetch_yfinance_snapshot
from app.domain.models.market_data import MarketDataBundle
from app.domain.usecases.kabutan_html_dir import ResolveKabutanHtmlDirUseCase, ResolvedKabutanHtmlDir
from app.domain.usecases.watchlist_path import ResolveWatchlistPathUseCase, ResolvedWatchlistPath
from app.domain.usecases.kabutan_forecast import FetchKabutanForecastUseCase
from app.domain.usecases.fundamental_analysis import FundamentalAnalysisService
from app.domain.usecases.fundamental_summary import FundamentalSummaryService
from app.domain.usecases.market_data import MarketDataService
from app.domain.builders.fundamental_summary import build_fundamental_summary_markdown
from app.domain.builders.technical_summary import build_technical_summary_markdown
from app.domain.builders.technical_output import build_technical_output
from app.domain.usecases.technical_analysis import TechnicalAnalysisService
from app.domain.usecases.technical_summary import TechnicalSummaryService
from app.presenters import build_fundamental_output
from app.services.cache_service import CacheService
from app.services.institutional_summary_service import InstitutionalSummaryService
from app.services.kabutan_html_dir_service import KabutanHtmlDirService
from app.services.kabutan_html_package_service import (
    KabutanHtmlPackageImportResult,
    KabutanHtmlPackageResult,
    KabutanHtmlPackageService,
)
from app.services.output_cache_service import OutputCacheService
from app.services.watchlist_service import WatchlistService

FUNDAMENTAL_SUMMARY_FILENAME_PREFIX = "fundamental_summary"
TECHNICAL_SUMMARY_FILENAME_PREFIX = "technical_summary"


def build_fundamental_summary_filename(*, today: date | None = None) -> str:
    target_date = today or date.today()
    return f"{FUNDAMENTAL_SUMMARY_FILENAME_PREFIX}-{target_date.isoformat()}.md"


def build_technical_summary_filename(*, generated_at: datetime | None = None) -> str:
    target = generated_at or datetime.now()
    return f"{TECHNICAL_SUMMARY_FILENAME_PREFIX}_{target.strftime('%m-%d-%H-%M')}.md"


def build_default_fundamental_service(file_cache: FileCache) -> FundamentalAnalysisService:
    kabutan_repository = KabutanForecastRepository(file_cache=file_cache)
    return FundamentalAnalysisService(
        file_cache=file_cache,
        fetch_market_snapshot=fetch_yfinance_snapshot,
        fetch_analyst_estimates=fetch_yfinance_analyst_estimates,
        fetch_kabutan_forecast_usecase=FetchKabutanForecastUseCase(
            repository=kabutan_repository
        ),
    )


def build_default_technical_service(file_cache: FileCache) -> TechnicalAnalysisService:
    return TechnicalAnalysisService(file_cache=file_cache)


def build_default_market_data_service(file_cache: FileCache) -> MarketDataService:
    return MarketDataService(file_cache=file_cache)


class FundamentalGuiController:
    """GUI層コントローラー: 表示以外のオーケストレーションを担当。"""

    def __init__(
        self,
        file_cache: FileCache | None = None,
        build_fundamental_service: Callable[[FileCache], FundamentalAnalysisService] | None = None,
        build_technical_service: Callable[[FileCache], TechnicalAnalysisService] | None = None,
        build_market_data_service: Callable[[FileCache], MarketDataService] | None = None,
    ):
        self.file_cache = file_cache or FileCache()
        self.cache_service = CacheService(self.file_cache)
        self.watchlist_service = WatchlistService(self.cache_service)
        self.kabutan_html_dir_service = KabutanHtmlDirService(self.cache_service)
        self.kabutan_html_package_service = KabutanHtmlPackageService()
        self.output_cache_service = OutputCacheService(self.cache_service)
        self.resolve_kabutan_html_dir_usecase = ResolveKabutanHtmlDirUseCase()
        self.resolve_watchlist_path_usecase = ResolveWatchlistPathUseCase()
        self._uses_default_fundamental_service = build_fundamental_service is None
        self._uses_default_technical_service = build_technical_service is None
        self.build_fundamental_service = build_fundamental_service or build_default_fundamental_service
        self.build_technical_service = build_technical_service or build_default_technical_service
        self.build_market_data_service = build_market_data_service or build_default_market_data_service
        self._market_data_bundle_cache: dict[str, MarketDataBundle] = {}

    def fetch_market_data_bundle(self, code4: str) -> MarketDataBundle:
        cached = self._market_data_bundle_cache.get(code4)
        if cached is not None:
            return cached
        bundle = self.build_market_data_service(self.file_cache).fetch_bundle(code4)
        self._market_data_bundle_cache[code4] = bundle
        return bundle

    def _build_default_fundamental_service_with_market_bundle(self, bundle: MarketDataBundle) -> FundamentalAnalysisService:
        kabutan_repository = KabutanForecastRepository(file_cache=self.file_cache)

        def fetch_market_snapshot(code4: str):
            if code4 == bundle.code4:
                return bundle.snapshot.to_dict()
            return fetch_yfinance_snapshot(code4)

        return FundamentalAnalysisService(
            file_cache=self.file_cache,
            fetch_market_snapshot=fetch_market_snapshot,
            fetch_analyst_estimates=fetch_yfinance_analyst_estimates,
            fetch_kabutan_forecast_usecase=FetchKabutanForecastUseCase(
                repository=kabutan_repository
            ),
        )

    def fetch_resolved_kabutan_html_dir(self) -> ResolvedKabutanHtmlDir:
        return self.kabutan_html_dir_service.resolve_cached_dir()

    def save_kabutan_html_dir_cache(self, path: Path) -> None:
        self.kabutan_html_dir_service.save_dir(path)

    def build_kabutan_html_package(
        self,
        *,
        source_dir: Path,
        output_dir: Path | None = None,
    ) -> KabutanHtmlPackageResult:
        return self.kabutan_html_package_service.build_package(
            source_dir=source_dir,
            output_dir=output_dir or (self.file_cache.base_dir / "kabutan_html_package"),
        )

    def import_kabutan_html_package(
        self,
        *,
        zip_path: Path,
        output_dir: Path | None = None,
    ) -> KabutanHtmlPackageImportResult:
        return self.kabutan_html_package_service.import_package(
            zip_path=zip_path,
            output_dir=output_dir or (self.file_cache.base_dir / "kabutan_html_imported_package"),
        )

    def fetch_resolved_watchlist_path(self) -> ResolvedWatchlistPath:
        cached_path = self.watchlist_service.restore_watchlist_path()
        return self.resolve_watchlist_path_usecase.fetch_resolved_watchlist_path(cached_path)

    def save_watchlist_path_cache(self, path: Path) -> None:
        self.watchlist_service.save_watchlist_path(path)

    def fetch_output_cache_for_today(self) -> dict[str, str]:
        return self.output_cache_service.fetch_for_today()

    def save_output_cache_for_today(self, output_cache: dict[str, str]) -> None:
        self.output_cache_service.save_for_today(output_cache)

    def fetch_watchlist_entries(self, path: Path) -> list[tuple[str, str]]:
        return self.watchlist_service.load_from_file(path)

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

        if self._uses_default_fundamental_service:
            bundle = self.fetch_market_data_bundle(code4)
            service = self._build_default_fundamental_service_with_market_bundle(bundle)
        else:
            service = self.build_fundamental_service(self.file_cache)
        output = service.build_analysis_output(
            name,
            code4,
            build_output_fn=build_fundamental_output,
            kabutan_html_dir=kabutan_html_dir,
        )
        output_cache[output_cache_key] = output
        return output

    def build_fundamental_summary_table(
        self,
        *,
        watchlist_entries: list[tuple[str, str]],
        kabutan_html_dir: Path | None = None,
    ) -> FundamentalSummaryTable:
        service = FundamentalSummaryService(self.build_fundamental_service(self.file_cache))
        return service.build_summary_table(watchlist_entries, kabutan_html_dir=kabutan_html_dir)

    def build_and_save_fundamental_summary(
        self,
        *,
        watchlist_entries: list[tuple[str, str]],
        output_dir: Path,
        kabutan_html_dir: Path | None = None,
        today: date | None = None,
    ) -> Path:
        table = self.build_fundamental_summary_table(
            watchlist_entries=watchlist_entries,
            kabutan_html_dir=kabutan_html_dir,
        )
        markdown = build_fundamental_summary_markdown(table)
        output_path = output_dir / build_fundamental_summary_filename(today=today)
        output_path.write_text(markdown, encoding="utf-8")
        return output_path

    def build_technical_summary_table(
        self,
        *,
        watchlist_entries: list[tuple[str, str]],
    ):
        service = TechnicalSummaryService(self._build_technical_summary_result)
        return service.build_summary_table(watchlist_entries)

    def build_and_save_technical_summary(
        self,
        *,
        watchlist_entries: list[tuple[str, str]],
        output_dir: Path,
        generated_at: datetime | None = None,
    ) -> Path:
        table = self.build_technical_summary_table(watchlist_entries=watchlist_entries)
        markdown = build_technical_summary_markdown(table)
        output_path = output_dir / build_technical_summary_filename(generated_at=generated_at)
        output_path.write_text(markdown, encoding="utf-8")
        return output_path

    def _build_technical_summary_result(self, name: str, code4: str):
        if self._uses_default_technical_service:
            bundle = self.fetch_market_data_bundle(code4)
            return TechnicalAnalysisService.build_analysis_result_from_bundle(name=name, bundle=bundle)
        service = self.build_technical_service(self.file_cache)
        return service.build_analysis_result(name=name, code4=code4)

    def fetch_technical_output(
        self,
        *,
        name: str,
        code4: str,
    ) -> str:
        if self._uses_default_technical_service:
            bundle = self.fetch_market_data_bundle(code4)
            result = TechnicalAnalysisService.build_analysis_result_from_bundle(name=name, bundle=bundle)
        else:
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
        service = InstitutionalSummaryService(
            file_cache=self.file_cache,
            build_fundamental_service=self.build_fundamental_service,
            build_technical_service=self.build_technical_service,
            uses_default_fundamental_service=self._uses_default_fundamental_service,
            uses_default_technical_service=self._uses_default_technical_service,
            fetch_market_data_bundle=self.fetch_market_data_bundle,
            build_fundamental_service_with_market_bundle=self._build_default_fundamental_service_with_market_bundle,
        )
        return service.build_text(name=name, code4=code4, kabutan_html_dir=kabutan_html_dir)


__all__ = [
    "FUNDAMENTAL_SUMMARY_FILENAME_PREFIX",
    "TECHNICAL_SUMMARY_FILENAME_PREFIX",
    "FundamentalGuiController",
    "build_fundamental_summary_filename",
    "build_technical_summary_filename",
    "build_default_market_data_service",
    "build_default_technical_service",
]
