"""Domain builder for fundamental analysis output text."""

from __future__ import annotations

from typing import Any

from app.domain.builders.fundamental_output_impl import build_fundamental_output_text_impl
from app.domain.models.financial_snapshot import FinancialMetricInputRow
from app.domain.models.kabutan_cashflow import KabutanCashflowRow
from app.domain.models.kabutan_forecast import KabutanForecastPair
from app.domain.builders.fundamental_output_impl import build_fundamental_output_sections_impl


def build_fundamental_output_text(
    *,
    name: str,
    code4: str,
    master: dict[str, Any] | None,
    price: float | None,
    market_cap: float | None,
    market_snapshot: dict[str, Any] | None = None,
    kabutan_forecast_pair: KabutanForecastPair | None = None,
) -> str:
    """ドメイン層の出力生成エントリポイント。"""
    return build_fundamental_output_text_impl(
        name=name,
        code4=code4,
        master=master,
        price=price,
        market_cap=market_cap,
        market_snapshot=market_snapshot,
        kabutan_forecast_pair=kabutan_forecast_pair,
    )


__all__ = ["build_fundamental_output_text"]


def build_fundamental_output_sections(
    *,
    name: str,
    code4: str,
    master: dict[str, Any] | None,
    price: float | None,
    market_cap: float | None,
    market_snapshot: dict[str, Any] | None = None,
    kabutan_forecast_pair: KabutanForecastPair | None = None,
    kabutan_cashflow_rows: tuple[KabutanCashflowRow, ...] = (),
    financial_metric_rows: tuple[FinancialMetricInputRow, ...] = (),
) -> "DisplaySections":
    return build_fundamental_output_sections_impl(
        name=name,
        code4=code4,
        master=master,
        price=price,
        market_cap=market_cap,
        market_snapshot=market_snapshot,
        kabutan_forecast_pair=kabutan_forecast_pair,
        kabutan_cashflow_rows=kabutan_cashflow_rows,
        financial_metric_rows=financial_metric_rows,
    )
