"""Presentation formatter for Kabutan forecast sections."""

from __future__ import annotations

from app.domain.builders.kabutan_output import build_kabutan_forecast_sections
from app.domain.models.cf_scoring_result import CfScoringResult
from app.domain.models.financial_snapshot import FinancialMetricInputRow
from app.domain.models.kabutan_cashflow import KabutanCashflowRow
from app.domain.models.kabutan_forecast import KabutanForecastPair
from app.domain.models.quarterly_financials import QuarterlyMetricRow
from app.presentation.display_formatter import format_sections


def build_kabutan_forecast_output(
    base_output: str,
    kabutan_forecast_pair: KabutanForecastPair | None,
    kabutan_source: str,
    kabutan_source_message: str | None,
    kabutan_cashflow_rows: tuple[KabutanCashflowRow, ...] = (),
    market_cap: float | None = None,
    financial_metric_rows: tuple[FinancialMetricInputRow, ...] = (),
    quarterly_metric_rows: tuple[QuarterlyMetricRow, ...] = (),
    quarterly_message: str | None = None,
    cf_scoring_result: CfScoringResult | None = None,
    include_financial_section: bool = True,
) -> str:
    sections = build_kabutan_forecast_sections(
        kabutan_forecast_pair,
        kabutan_source,
        kabutan_source_message,
        kabutan_cashflow_rows,
        market_cap,
        financial_metric_rows,
        quarterly_metric_rows,
        quarterly_message,
        include_financial_section,
    )
    section = format_sections(sections)
    return f"{base_output}\n{section}"


__all__ = ["build_kabutan_forecast_output"]
