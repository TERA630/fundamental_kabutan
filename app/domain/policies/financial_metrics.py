"""Domain policy for financial metric calculations."""

from __future__ import annotations


DEFAULT_EFFECTIVE_TAX_RATE = 0.30


def calc_roe(net_income: int | float | None, equity: int | float | None) -> float | None:
    """ROE(%) = 当期純利益 / 自己資本 * 100."""
    if net_income is None or equity in (None, 0):
        return None
    return (float(net_income) / float(equity)) * 100


def calc_pbr(price: int | float | None, bps: int | float | None) -> float | None:
    """PBR(倍) = 株価 / BPS."""
    if price is None or bps in (None, 0):
        return None
    return float(price) / float(bps)


def calc_roic_approx(
    operating_profit: int | float | None,
    equity: int | float | None,
    interest_bearing_debt: int | float | None,
    tax_rate: float = DEFAULT_EFFECTIVE_TAX_RATE,
) -> float | None:
    """ROIC(近似, %) = 税引後営業利益 / (自己資本 + 有利子負債) * 100."""
    if operating_profit is None or equity is None or interest_bearing_debt is None:
        return None
    invested_capital = float(equity) + float(interest_bearing_debt)
    if invested_capital == 0:
        return None
    nopat = float(operating_profit) * (1 - float(tax_rate))
    return (nopat / invested_capital) * 100


__all__ = [
    "DEFAULT_EFFECTIVE_TAX_RATE",
    "calc_pbr",
    "calc_roe",
    "calc_roic_approx",
]
