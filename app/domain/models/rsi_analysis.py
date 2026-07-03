"""Domain models for intraday RSI analysis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

RsiDirectionSymbol = Literal["↑", "↓", "→", "N/A"]
RsiDirectionLabel = Literal["上昇中", "低下中", "横ばい", "N/A"]
RsiLevelLabel = Literal[
    "過熱後半",
    "やや過熱",
    "勢い良好",
    "勢い改善",
    "高止まり",
    "勢い鈍化",
    "反発弱い",
    "底打ち初動",
    "売られ過ぎ",
    "中立",
    "N/A",
]
RsiDivergenceLabel = Literal[
    "上昇鈍化",
    "勢い追随",
    "底打ち兆候",
    "反発弱い",
    "底堅い",
    "明確な乖離なし",
    "N/A",
]
RsiOverallLabel = Literal[
    "勢い良好",
    "勢い改善",
    "高止まり",
    "短期鈍化",
    "上昇鈍化警戒",
    "底打ち確認待ち",
    "底打ち初動",
    "N/A",
]


@dataclass(frozen=True)
class RsiSignal:
    value: float | None
    delta: float | None
    direction_symbol: RsiDirectionSymbol
    direction_label: RsiDirectionLabel
    level_label: RsiLevelLabel


@dataclass(frozen=True)
class RsiDivergence:
    label: RsiDivergenceLabel
    detail: str


@dataclass(frozen=True)
class RsiAnalysis:
    five_min: RsiSignal
    hourly: RsiSignal
    five_min_divergence: RsiDivergence
    hourly_divergence: RsiDivergence
    overall_label: RsiOverallLabel


__all__ = [
    "RsiAnalysis",
    "RsiDirectionLabel",
    "RsiDirectionSymbol",
    "RsiDivergence",
    "RsiDivergenceLabel",
    "RsiLevelLabel",
    "RsiOverallLabel",
    "RsiSignal",
]
