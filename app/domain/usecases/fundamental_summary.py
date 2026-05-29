"""Domain use-case: build fundamental summary rows for a watchlist."""

from __future__ import annotations

from pathlib import Path

from app.domain.models.cf_scoring_result import CategoryScore, CfScoringResult
from app.domain.models.fundamental_summary import (
    FundamentalSummaryRow,
    FundamentalSummaryTable,
    SkippedSummaryStock,
)
from app.domain.models.kabutan_forecast import KabutanForecastPair
from app.domain.policies.cf_scoring import calculate_cf_score
from app.domain.policies.financial_metrics import calc_roic_approx
from app.domain.usecases.fundamental_analysis import FundamentalAnalysisService


class FundamentalSummaryService:
    """Builds sortable summary rows from watchlist entries."""

    def __init__(self, fundamental_analysis_service: FundamentalAnalysisService):
        self.fundamental_analysis_service = fundamental_analysis_service

    def build_summary_table(
        self,
        watchlist_entries: list[tuple[str, str]] | tuple[tuple[str, str], ...],
        *,
        kabutan_html_dir: Path | None = None,
    ) -> FundamentalSummaryTable:
        rows: list[FundamentalSummaryRow] = []
        skipped: list[SkippedSummaryStock] = []

        for name, code4 in watchlist_entries:
            try:
                row = self.build_summary_row(name=name, code4=code4, kabutan_html_dir=kabutan_html_dir)
            except Exception as exc:
                skipped.append(SkippedSummaryStock(name=name, code4=code4, reason=str(exc)))
                continue
            if row is None:
                skipped.append(SkippedSummaryStock(name=name, code4=code4, reason="総合スコア作成不可"))
                continue
            rows.append(row)

        return FundamentalSummaryTable(rows=tuple(sorted(rows, key=self._sort_key)), skipped=tuple(skipped))

    def build_summary_row(
        self,
        *,
        name: str,
        code4: str,
        kabutan_html_dir: Path | None = None,
    ) -> FundamentalSummaryRow | None:
        service = self.fundamental_analysis_service
        price_snapshot = service.fetch_price_snapshot(code4)
        kabutan_fetch_result = service.fetch_kabutan_forecast_pair(code4, html_dir=kabutan_html_dir)
        financial_metric_rows = service.build_financial_metric_rows(
            price=price_snapshot.get("price"),
            forecast_pair=kabutan_fetch_result.pair,
            balance_sheet_rows=kabutan_fetch_result.balance_sheet_rows,
        )
        cf_scoring_input = service.build_cf_scoring_input(
            code4=code4,
            as_of=service.resolve_cf_scoring_as_of(
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
        if cf_scoring_input is None:
            return None

        scoring_result = calculate_cf_score(cf_scoring_input)
        latest_financial_row = max(financial_metric_rows, key=lambda row: row.year) if financial_metric_rows else None
        roic = (
            calc_roic_approx(
                latest_financial_row.operating_profit,
                latest_financial_row.equity,
                latest_financial_row.interest_bearing_debt,
            )
            if latest_financial_row is not None
            else None
        )

        return FundamentalSummaryRow(
            name=name,
            code4=code4,
            total_score=scoring_result.total.total_points,
            quality_score=self._category_score_or_none(scoring_result.quality),
            growth_score=self._category_score_or_none(scoring_result.growth),
            valuation_score=self._category_score_or_none(scoring_result.valuation),
            roic=roic,
            operating_margin=self._latest_operating_margin(kabutan_fetch_result.pair),
            cash_conversion=self._cash_conversion(scoring_result),
            per=cf_scoring_input.per,
        )

    @staticmethod
    def _category_score_or_none(category_score: CategoryScore) -> int | None:
        if all(metric.raw_value is None for metric in category_score.metrics):
            return None
        return category_score.subtotal

    @staticmethod
    def _latest_operating_margin(forecast_pair: KabutanForecastPair | None) -> float | None:
        if forecast_pair is None or not forecast_pair.all_rows:
            return None
        latest_row = max(forecast_pair.all_rows, key=lambda row: (row.year, row.month))
        if latest_row.sales in (None, 0) or latest_row.operating_profit is None:
            return None
        return (latest_row.operating_profit / latest_row.sales) * 100

    @staticmethod
    def _cash_conversion(scoring_result: CfScoringResult) -> float | None:
        for metric in scoring_result.quality.metrics:
            if metric.metric_id == "cash_conversion_np":
                return metric.raw_value
        return None

    @staticmethod
    def _sort_key(row: FundamentalSummaryRow) -> tuple[int, int, int, str]:
        return (
            -row.total_score,
            -(row.growth_score or 0),
            -(row.quality_score or 0),
            row.code4,
        )


__all__ = ["FundamentalSummaryService"]
