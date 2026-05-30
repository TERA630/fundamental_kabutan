"""Domain models for watchlist-level fundamental summary output."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FundamentalSummaryRow:
    name: str
    code4: str
    total_score: int
    quality_score: int | None
    growth_score: int | None
    valuation_score: int | None
    operating_margin: float | None
    operating_profit_cagr_3y: float | None
    roic: float | None
    cash_conversion: float | None
    per: float | None
    investment_rate: float | None


@dataclass(frozen=True)
class SkippedSummaryStock:
    name: str
    code4: str
    reason: str


@dataclass(frozen=True)
class FundamentalSummaryTable:
    rows: tuple[FundamentalSummaryRow, ...]
    skipped: tuple[SkippedSummaryStock, ...] = ()


__all__ = [
    "FundamentalSummaryRow",
    "FundamentalSummaryTable",
    "SkippedSummaryStock",
]
