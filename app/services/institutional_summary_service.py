"""Service for building the fixed institutional summary panel."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from app.data.file_cache import FileCache
from app.domain.builders.institutional_summary import build_institutional_summary_text
from app.domain.models.market_data import MarketDataBundle
from app.domain.policies.cf_scoring import calculate_cf_score
from app.domain.policies.institutional_summary import build_institutional_summary
from app.domain.usecases.fundamental_analysis import FundamentalAnalysisService
from app.domain.usecases.technical_analysis import TechnicalAnalysisService


class InstitutionalSummaryService:
    def __init__(
        self,
        *,
        file_cache: FileCache,
        build_fundamental_service: Callable[[FileCache], FundamentalAnalysisService],
        build_technical_service: Callable[[FileCache], TechnicalAnalysisService],
        uses_default_fundamental_service: bool,
        uses_default_technical_service: bool,
        fetch_market_data_bundle: Callable[[str], MarketDataBundle],
        build_fundamental_service_with_market_bundle: Callable[[MarketDataBundle], FundamentalAnalysisService],
    ):
        self.file_cache = file_cache
        self.build_fundamental_service = build_fundamental_service
        self.build_technical_service = build_technical_service
        self.uses_default_fundamental_service = uses_default_fundamental_service
        self.uses_default_technical_service = uses_default_technical_service
        self.fetch_market_data_bundle = fetch_market_data_bundle
        self.build_fundamental_service_with_market_bundle = build_fundamental_service_with_market_bundle

    def build_text(
        self,
        *,
        name: str,
        code4: str,
        kabutan_html_dir: Path | None = None,
    ) -> str:
        technical_result, fundamental_service, price_snapshot = self._resolve_inputs(name=name, code4=code4)
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
            market_cap_yen=_number_or_none(price_snapshot.get("market_cap")),
            close=technical_result.snapshot.price.close,
            volume=technical_result.snapshot.price.volume,
            volume_avg20=technical_result.snapshot.price.volume_avg20,
            roic_pct=cf_scoring_input.roic if cf_scoring_input is not None else None,
            eps_cagr_pct=cf_scoring_input.eps_cagr_3y if cf_scoring_input is not None else None,
            fundamental_score=scoring_result.total.total_points if scoring_result is not None else None,
            fundamental_rank=scoring_result.total.judgement if scoring_result is not None else None,
            latest=technical_result.snapshot.price.latest,
            vwap=_number_or_none(technical_result.vwap_snapshot.get("vwap")),
            ma5=technical_result.snapshot.moving_average.ma5,
            ma25=technical_result.snapshot.moving_average.ma25,
            vwap_is_daily_reference=technical_result.vwap_snapshot.get("vwap_source") == "日足参考値",
        )
        return build_institutional_summary_text(summary)

    def _resolve_inputs(self, *, name: str, code4: str) -> tuple[Any, FundamentalAnalysisService, dict[str, Any]]:
        if self.uses_default_technical_service and self.uses_default_fundamental_service:
            bundle = self.fetch_market_data_bundle(code4)
            technical_result = TechnicalAnalysisService.build_analysis_result_from_bundle(name=name, bundle=bundle)
            fundamental_service = self.build_fundamental_service_with_market_bundle(bundle)
            return technical_result, fundamental_service, bundle.snapshot.to_dict()

        technical_service = self.build_technical_service(self.file_cache)
        technical_result = technical_service.build_analysis_result(name=name, code4=code4)
        fundamental_service = self.build_fundamental_service(self.file_cache)
        return technical_result, fundamental_service, fundamental_service.fetch_price_snapshot(code4)


def _number_or_none(value: Any) -> float | None:
    return value if isinstance(value, (int, float)) else None

