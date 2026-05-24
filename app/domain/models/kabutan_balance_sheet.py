"""Domain models for Kabutan balance sheet rows."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KabutanBalanceSheetRow:
    period_label: str
    year: int
    month: int
    bps: float | None
    equity_ratio: float | None
    total_assets: int | None
    equity: int | None
    retained_earnings: int | None
    interest_bearing_debt_multiple: float | None


__all__ = ["KabutanBalanceSheetRow"]
