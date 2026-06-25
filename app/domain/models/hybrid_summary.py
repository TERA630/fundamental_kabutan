"""Domain models for watchlist-level hybrid summary output."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

HybridSummaryTag = Literal["F1", "F2", "M1", "M2"]


@dataclass(frozen=True)
class HybridSummaryRow:
    name: str
    code4: str
    tag: HybridSummaryTag
    tag_label: str
    fundamental_score: int
    quality_score: int | None
    technical_rank: str
    technical_rank_label: str
    latest: float | None
    dev25_pct: float | None
    vwap_diff_pct: float | None
    day_close_position: float | None
    volume_vs_avg20_pct: float | None
    collapse_risk_score: int | None
    resistance_upside_pct: float | None
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class SkippedHybridSummaryStock:
    name: str
    code4: str
    reason: str


@dataclass(frozen=True)
class HybridSummaryTable:
    rows: tuple[HybridSummaryRow, ...]
    skipped: tuple[SkippedHybridSummaryStock, ...] = ()


__all__ = [
    "HybridSummaryRow",
    "HybridSummaryTable",
    "HybridSummaryTag",
    "SkippedHybridSummaryStock",
]
