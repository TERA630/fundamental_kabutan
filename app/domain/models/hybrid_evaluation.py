"""Domain models for single-stock Hybrid evaluation output."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


HybridEvaluationTag = Literal["F1", "F2", "M1", "M2"]


@dataclass(frozen=True)
class HybridEvaluation:
    name: str
    code4: str
    tag: HybridEvaluationTag | None
    tag_label: str | None
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
    reasons: tuple[str, ...] = ()

    @property
    def matched(self) -> bool:
        return self.tag is not None


__all__ = ["HybridEvaluation", "HybridEvaluationTag"]
