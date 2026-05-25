"""Domain models for quarterly actuals and year-over-year growth metrics."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Quarter(str, Enum):
    Q1 = "Q1"
    Q2 = "Q2"
    Q3 = "Q3"
    Q4 = "Q4"


class YoYStatus(str, Enum):
    OK = "ok"
    NA = "na"
    TURNAROUND_TO_PROFIT = "turnaround_to_profit"


class GrowthMetricKind(str, Enum):
    OPERATING_PROFIT = "operating_profit"
    OPERATING_MARGIN = "operating_margin"
    REVISED_EPS = "revised_eps"


@dataclass(frozen=True)
class QuarterlyActual:
    ticker: str
    fiscal_year: int
    quarter: Quarter
    sales: int | None
    ordinary_profit: int | None
    operating_profit: int | None
    revised_eps: float | None
    operating_margin: float | None


@dataclass(frozen=True)
class YoYMetric:
    status: YoYStatus
    value_pct: float | None


@dataclass(frozen=True)
class QuarterlyGrowthMetrics:
    operating_profit_yoy: YoYMetric
    operating_margin_yoy: YoYMetric
    revised_eps_yoy: YoYMetric


@dataclass(frozen=True)
class QuarterlyActualWithGrowth:
    current: QuarterlyActual
    prior_same_quarter: QuarterlyActual | None
    growth: QuarterlyGrowthMetrics


__all__ = [
    "GrowthMetricKind",
    "Quarter",
    "QuarterlyActual",
    "QuarterlyActualWithGrowth",
    "QuarterlyGrowthMetrics",
    "YoYMetric",
    "YoYStatus",
]
