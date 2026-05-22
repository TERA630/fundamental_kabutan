"""Domain models for display-oriented fundamental snapshot."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal


@dataclass(frozen=True)
class StockProfile:
    code4: str
    name: str
    industry_name: str | None
    market_cap_billion_yen: float | None
    size_class_label: str | None


@dataclass(frozen=True)
class PriceSnapshot:
    price_yen: float | None
    as_of_date: date | None


@dataclass(frozen=True)
class ValuationMetrics:
    per: float | None
    eps_yen: float | None
    dividend_yield_pct: float | None


@dataclass(frozen=True)
class PeriodFundamentalRow:
    period_kind: Literal["actual", "forecast"]
    fiscal_year: int
    sales_hundred_million_yen: float | None
    operating_profit_hundred_million_yen: float | None
    ordinary_profit_hundred_million_yen: float | None
    final_profit_hundred_million_yen: float | None
    eps_yen: float | None
    dividend_yen: float | None
    operating_margin_pct: float | None = None
    ordinary_margin_pct: float | None = None
    operating_growth_yoy_pct: float | None = None


@dataclass(frozen=True)
class FundamentalDisplaySnapshot:
    profile: StockProfile
    price: PriceSnapshot
    metrics_actual: ValuationMetrics | None
    metrics_current_forecast: ValuationMetrics | None
    metrics_next_forecast: ValuationMetrics | None
    rows: tuple[PeriodFundamentalRow, ...]


__all__ = [
    "StockProfile",
    "PriceSnapshot",
    "ValuationMetrics",
    "PeriodFundamentalRow",
    "FundamentalDisplaySnapshot",
]
