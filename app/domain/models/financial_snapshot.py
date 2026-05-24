"""Domain model for yearly financial metric input candidates."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FinancialMetricInputRow:
    year: int
    net_income: int | None
    equity: int | None
    operating_profit: int | None
    interest_bearing_debt: int | None
    bps: float | None
    price: float | None


__all__ = ["FinancialMetricInputRow"]
