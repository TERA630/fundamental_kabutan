"""Domain policy for growth metric calculations."""

from __future__ import annotations


def calc_operating_growth_rate(previous_operating_profit: int | None, current_operating_profit: int | None) -> float | None:
    if previous_operating_profit is None or current_operating_profit is None or previous_operating_profit == 0:
        return None
    return ((current_operating_profit - previous_operating_profit) / previous_operating_profit) * 100


def calc_eps_growth_rate(previous_eps: float | None, current_eps: float | None) -> float | None:
    if previous_eps is None or current_eps is None:
        return None
    if previous_eps == 0:
        return None
    return ((current_eps - previous_eps) / previous_eps) * 100


def calc_cagr(start_value: float | int | None, end_value: float | int | None, years: int) -> float | None:
    if start_value is None or end_value is None or years <= 0:
        return None
    start = float(start_value)
    end = float(end_value)
    if start <= 0 or end < 0:
        return None
    return ((end / start) ** (1 / years) - 1) * 100


__all__ = [
    "calc_operating_growth_rate",
    "calc_eps_growth_rate",
    "calc_cagr",
]
