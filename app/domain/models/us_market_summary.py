"""Domain models for US market technical summary output."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class UsMarketSummaryRow:
    name: str
    ticker: str
    latest: float | None
    day_change_pct: float | None
    dev5_pct: float | None
    dev25_pct: float | None
    rsi14: float | None


@dataclass(frozen=True)
class SkippedUsMarketSummaryItem:
    name: str
    ticker: str
    reason: str


@dataclass(frozen=True)
class UsMarketSummaryTable:
    as_of: datetime
    rows: tuple[UsMarketSummaryRow, ...]
    skipped: tuple[SkippedUsMarketSummaryItem, ...] = ()


__all__ = [
    "SkippedUsMarketSummaryItem",
    "UsMarketSummaryRow",
    "UsMarketSummaryTable",
]
