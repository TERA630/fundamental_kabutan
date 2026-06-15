"""Domain result models for rankCF scoring."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Rank = Literal["S", "A", "B", "C", "D", "E", "N/A"]
Category = Literal["quality", "growth", "valuation"]


@dataclass(frozen=True)
class MetricScore:
    metric_id: str
    category: Category
    raw_value: float | None
    rank: Rank
    points: int
    max_points: int
    rule_notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class CategoryScore:
    category: Category
    subtotal: int
    max_points: int
    metrics: tuple[MetricScore, ...]


@dataclass(frozen=True)
class TotalScore:
    total_points: int
    max_points: int
    judgement: str
    investment_category: str
    priority_hint: str | None


@dataclass(frozen=True)
class CfScoringResult:
    version: str
    as_of: str | None
    quality: CategoryScore
    growth: CategoryScore
    valuation: CategoryScore
    total: TotalScore


__all__ = [
    "Category",
    "CategoryScore",
    "CfScoringResult",
    "MetricScore",
    "Rank",
    "TotalScore",
]
