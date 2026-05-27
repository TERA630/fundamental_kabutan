"""Presentation helpers: bridge GUI use-cases and domain/output builders."""

from __future__ import annotations
from typing import Any

from app.domain.builders.fundamental_output import build_fundamental_output_text
from app.domain.builders.kabutan_output import build_kabutan_forecast_output
from app.domain.models.kabutan_cashflow import KabutanCashflowRow
from app.domain.models.kabutan_forecast import KabutanForecastPair
from app.domain.models.financial_snapshot import FinancialMetricInputRow
from app.domain.models.quarterly_financials import QuarterlyMetricRow
from app.domain.models.cf_scoring_result import CfScoringResult


def build_fundamental_output(
    *,
    name: str,
    code4: str,
    master: dict[str, Any] | None,
    price: float | None,
    market_cap: float | None,
    market_snapshot: dict[str, Any] | None = None,
    kabutan_forecast_pair: KabutanForecastPair | None = None,
    kabutan_source: str = "none",
    kabutan_source_message: str | None = None,
    kabutan_cashflow_rows: tuple[KabutanCashflowRow, ...] = (),
    financial_metric_rows: tuple[FinancialMetricInputRow, ...] = (),
    quarterly_metric_rows: tuple[QuarterlyMetricRow, ...] = (),
    quarterly_message: str | None = None,
    cf_scoring_result: CfScoringResult | None = None,
) -> str:
    """ドメイン層の出力生成ビルダーを呼び出す。"""
    base_output = build_fundamental_output_text(
        name=name,
        code4=code4,
        master=master,
        price=price,
        market_cap=market_cap,
        market_snapshot=market_snapshot,
        kabutan_forecast_pair=kabutan_forecast_pair,
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
    )
