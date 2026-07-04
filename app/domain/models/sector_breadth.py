"""Domain models for sector breadth evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SectorBreadthJudgement = Literal[
    "強い上昇地合い",
    "押し目買い優勢",
    "まちまち",
    "戻り売り優勢",
    "崩れ地合い",
    "判定不可",
]


@dataclass(frozen=True)
class SectorBreadthRatio:
    count: int
    total: int
    ratio: float | None


@dataclass(frozen=True)
class SectorBreadthRow:
    sector: str
    judgement: SectorBreadthJudgement
    vwap_above: SectorBreadthRatio
    terminal_position_median: float | None
    ma25_above: SectorBreadthRatio
    collapse_score_median: float | None
    volume_vs_avg20_median_pct: float | None
    volume_spike_bearish_count: int
    comment: str


@dataclass(frozen=True)
class SectorBreadthTable:
    rows: tuple[SectorBreadthRow, ...]


__all__ = [
    "SectorBreadthJudgement",
    "SectorBreadthRatio",
    "SectorBreadthRow",
    "SectorBreadthTable",
]
