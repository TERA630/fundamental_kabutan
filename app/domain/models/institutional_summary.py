"""Domain models for institutional investment summary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

TechnicalSignal = Literal["○", "×", "N/A"]
MarketCapClass = Literal["超大型", "大型主役", "中型主役", "小型"]


@dataclass(frozen=True)
class InstitutionalScoreBreakdown:
    market_cap: int
    trading_value: int
    roic: int
    eps_cagr: int

    @property
    def total(self) -> int:
        return self.market_cap + self.trading_value + self.roic + self.eps_cagr


@dataclass(frozen=True)
class TechnicalConditionSummary:
    vwap: TechnicalSignal
    ma5: TechnicalSignal
    ma25: TechnicalSignal
    vwap_is_daily_reference: bool = False


@dataclass(frozen=True)
class InstitutionalSummary:
    market_cap_yen: float | None
    market_cap_class: MarketCapClass | None
    volume: float | None
    volume_avg20: float | None
    volume_vs_avg20_pct: float | None
    trading_value_yen: float | None
    score: InstitutionalScoreBreakdown
    fundamental_score: int | None
    fundamental_rank: str | None
    technical: TechnicalConditionSummary


__all__ = [
    "InstitutionalScoreBreakdown",
    "InstitutionalSummary",
    "MarketCapClass",
    "TechnicalConditionSummary",
    "TechnicalSignal",
]
