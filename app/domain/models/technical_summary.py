"""Domain models for watchlist-level technical summary output."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.domain.models.us_market_summary import UsMarketSummaryTable

TechnicalSummaryRank = Literal["A1", "A2", "B1", "B2", "C1", "C2", "E"]


@dataclass(frozen=True)
class TechnicalSummaryLine:
    label: str
    price: float


@dataclass(frozen=True)
class TechnicalSummaryRow:
    name: str
    code4: str
    rank: TechnicalSummaryRank
    rank_label: str
    latest: float | None
    day_change_price: float | None
    day_change_pct: float | None
    three_session_change_pct: float | None
    day_high: float | None
    day_low: float | None
    day_range_pct: float | None
    day_range_atr: float | None
    vwap: float | None
    vwap_diff_pct: float | None
    dev25_pct: float | None
    ma25_distance_atr: float | None
    volume_vs_avg20_pct: float | None
    previous_vwap_maintained: bool | None
    support_lines: tuple[TechnicalSummaryLine, ...]
    resistance_lines: tuple[TechnicalSummaryLine, ...]
    recent60_range_position: float | None


@dataclass(frozen=True)
class SkippedTechnicalSummaryStock:
    name: str
    code4: str
    reason: str


@dataclass(frozen=True)
class TechnicalSummaryTable:
    rows: tuple[TechnicalSummaryRow, ...]
    skipped: tuple[SkippedTechnicalSummaryStock, ...] = ()
    us_market: UsMarketSummaryTable | None = None


__all__ = [
    "SkippedTechnicalSummaryStock",
    "TechnicalSummaryLine",
    "TechnicalSummaryRank",
    "TechnicalSummaryRow",
    "TechnicalSummaryTable",
]
