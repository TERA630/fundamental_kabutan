"""Domain models for watchlist-level technical summary output."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.domain.models.signal_atom import SignalAtom
from app.domain.models.us_market_summary import UsMarketSummaryTable

TechnicalSummaryRank = Literal["B2", "B1", "A2", "A1", "A1弱", "C2", "C1", "D1", "D2", "D3", "E"]
CollapseRiskLevel = Literal["低", "中", "高"]
HoldJudgement = Literal["◎", "○", "△", "×"]


@dataclass(frozen=True)
class TechnicalHeadlineSummary:
    rank: TechnicalSummaryRank
    rank_label: str
    comment: str
    next_action: str
    collapse_state_label: str | None = "崩れ条件なし"
    c2_fall_reason: str | None = None

    @property
    def text(self) -> str:
        return f"{self.rank} {self.rank_label}｜{self.comment}｜{self.next_action}"


@dataclass(frozen=True)
class TechnicalPositionAssessment:
    collapse_risk_score: int
    collapse_risk_level: CollapseRiskLevel
    collapse_risk_label: str
    hold_judgement: HoldJudgement
    bottoming_start_established: bool
    collapse_risk_signals: tuple[SignalAtom, ...] = ()


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
    day_close_position: float | None
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
    collapse_risk_score: int | None = None
    headline_comment: str = ""
    next_action: str = ""
    high_breakout_count: int | None = None
    low_higher_count: int | None = None
    low_lower_count: int | None = None
    previous_low_maintained: bool | None = None
    volume_spike_bearish: bool | None = None


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
    "CollapseRiskLevel",
    "HoldJudgement",
    "SkippedTechnicalSummaryStock",
    "TechnicalHeadlineSummary",
    "TechnicalPositionAssessment",
    "TechnicalSummaryLine",
    "TechnicalSummaryRank",
    "TechnicalSummaryRow",
    "TechnicalSummaryTable",
]
