"""Domain models for Kabutan cashflow rows."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KabutanCashflowRow:
    period_label: str
    year: int
    month: int
    free_cf: int | None
    operating_cf: int | None
    investing_cf: int | None
    financing_cf: int | None
    cash_stock: int | None


__all__ = ["KabutanCashflowRow"]
