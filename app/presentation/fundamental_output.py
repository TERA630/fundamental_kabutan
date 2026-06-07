"""Fundamental output formatting orchestration."""

from __future__ import annotations

import logging
from typing import Any

from app.domain.builders.fundamental_output import (
    build_fundamental_output_sections,
    build_fundamental_output_text,
)
from app.domain.builders.kabutan_output import build_kabutan_forecast_output
from app.domain.models.analyst_estimates import AnalystEstimates
from app.domain.models.cf_scoring_result import CfScoringResult
from app.domain.models.financial_snapshot import FinancialMetricInputRow
from app.domain.models.kabutan_cashflow import KabutanCashflowRow
from app.domain.models.kabutan_forecast import KabutanForecastPair
from app.domain.models.quarterly_financials import QuarterlyMetricRow
from app.presentation.cf_scoring_output import merge_scoring_sections
from app.presentation.display_formatter import format_sections
from app.presentation.legacy_fallback import append_scoring_fallback

logger = logging.getLogger(__name__)


def build_base_fundamental_output(
    *,
    name: str,
    code4: str,
    master: dict[str, Any] | None,
    price: float | None,
    market_cap: float | None,
    market_snapshot: dict[str, Any] | None = None,
    analyst_estimates: AnalystEstimates | None = None,
    kabutan_forecast_pair: KabutanForecastPair | None = None,
    kabutan_cashflow_rows: tuple[KabutanCashflowRow, ...] = (),
    financial_metric_rows: tuple[FinancialMetricInputRow, ...] = (),
    cf_scoring_result: CfScoringResult | None = None,
    growth_phase: str | None = None,
    per_level: str | None = None,
    roic_level: str | None = None,
    operating_profit_cagr_3y: float | None = None,
) -> str:
    base_output = build_fundamental_output_text(
        name=name,
        code4=code4,
        master=master,
        price=price,
        market_cap=market_cap,
        market_snapshot=market_snapshot,
        analyst_estimates=analyst_estimates,
        kabutan_forecast_pair=kabutan_forecast_pair,
    )
    try:
        sections = build_fundamental_output_sections(
            name=name,
            code4=code4,
            master=master,
            price=price,
            market_cap=market_cap,
            market_snapshot=market_snapshot,
            analyst_estimates=analyst_estimates,
            kabutan_forecast_pair=kabutan_forecast_pair,
            kabutan_cashflow_rows=kabutan_cashflow_rows,
            financial_metric_rows=financial_metric_rows,
        )
        if cf_scoring_result is not None:
            sections = merge_scoring_sections(
                sections,
                cf_scoring_result,
                growth_phase=growth_phase,
                operating_profit_cagr_3y=operating_profit_cagr_3y,
                per_level=per_level,
                roic_level=roic_level,
            )
        return format_sections(sections)
    except Exception:
        logger.debug("DTO formatting path failed, using legacy text builder", exc_info=True)
    return append_scoring_fallback(base_output, cf_scoring_result)


def build_fundamental_output(
    *,
    name: str,
    code4: str,
    master: dict[str, Any] | None,
    price: float | None,
    market_cap: float | None,
    market_snapshot: dict[str, Any] | None = None,
    analyst_estimates: AnalystEstimates | None = None,
    kabutan_forecast_pair: KabutanForecastPair | None = None,
    kabutan_source: str = "none",
    kabutan_source_message: str | None = None,
    kabutan_cashflow_rows: tuple[KabutanCashflowRow, ...] = (),
    financial_metric_rows: tuple[FinancialMetricInputRow, ...] = (),
    quarterly_metric_rows: tuple[QuarterlyMetricRow, ...] = (),
    quarterly_message: str | None = None,
    cf_scoring_result: CfScoringResult | None = None,
    growth_phase: str | None = None,
    per_level: str | None = None,
    roic_level: str | None = None,
    operating_profit_cagr_3y: float | None = None,
) -> str:
    base_output = build_base_fundamental_output(
        name=name,
        code4=code4,
        master=master,
        price=price,
        market_cap=market_cap,
        market_snapshot=market_snapshot,
        analyst_estimates=analyst_estimates,
        kabutan_forecast_pair=kabutan_forecast_pair,
        kabutan_cashflow_rows=kabutan_cashflow_rows,
        financial_metric_rows=financial_metric_rows,
        cf_scoring_result=cf_scoring_result,
        growth_phase=growth_phase,
        per_level=per_level,
        roic_level=roic_level,
        operating_profit_cagr_3y=operating_profit_cagr_3y,
    )
    return build_kabutan_forecast_output(
        base_output,
        kabutan_forecast_pair,
        kabutan_source,
        kabutan_source_message,
        kabutan_cashflow_rows,
        market_cap,
        financial_metric_rows,
        quarterly_metric_rows,
        quarterly_message,
        cf_scoring_result,
        False,
    )

