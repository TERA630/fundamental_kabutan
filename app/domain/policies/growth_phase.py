"""Domain policy for growth phase classification."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.domain.models.kabutan_forecast import KabutanForecastRow
from app.domain.policies.growth_metrics import calc_cagr, calc_eps_growth_rate, calc_operating_growth_rate
from app.domain.policies.growth_rows import build_growth_rows


GrowthPhase = Literal[
    "業績回復途上",
    "成長再加速",
    "高成長鈍化後",
    "高成長中",
    "利益改善型",
    "低成長",
    "安定成長",
]


@dataclass(frozen=True)
class GrowthPhaseInput:
    sales_growth_current: float | None = None
    op_growth_current: float | None = None
    eps_growth_current: float | None = None
    sales_growth_previous: float | None = None
    op_growth_previous: float | None = None
    eps_growth_previous: float | None = None
    sales_cagr_3y: float | None = None
    op_cagr_3y: float | None = None
    eps_cagr_3y: float | None = None
    previous_op: int | None = None
    current_op: int | None = None
    previous_eps: float | None = None
    current_eps: float | None = None


def classify_growth_phase(data: GrowthPhaseInput) -> GrowthPhase:
    if _is_recovery_phase(data):
        return "業績回復途上"
    if _is_growth_reaccelerating(data):
        return "成長再加速"
    if _is_high_growth_after_slowdown(data):
        return "高成長鈍化後"
    if _is_high_growth(data):
        return "高成長中"
    if _is_profit_improving(data):
        return "利益改善型"
    if _is_low_growth(data):
        return "低成長"
    return "安定成長"


def build_growth_phase_input(rows: list[KabutanForecastRow] | tuple[KabutanForecastRow, ...]) -> GrowthPhaseInput:
    growth_rows = build_growth_rows(list(rows))
    if len(growth_rows) < 2:
        return GrowthPhaseInput()

    current_row = growth_rows[-1]
    previous_row = growth_rows[-2]
    previous2_row = growth_rows[-3] if len(growth_rows) >= 3 else None

    sales_growth_current = _calc_growth_rate(previous_row.sales, current_row.sales)
    op_growth_current = calc_operating_growth_rate(previous_row.operating_profit, current_row.operating_profit)
    eps_growth_current = calc_eps_growth_rate(previous_row.revised_eps, current_row.revised_eps)

    sales_growth_previous = _calc_growth_rate(previous2_row.sales, previous_row.sales) if previous2_row is not None else None
    op_growth_previous = (
        calc_operating_growth_rate(previous2_row.operating_profit, previous_row.operating_profit)
        if previous2_row is not None
        else None
    )
    eps_growth_previous = (
        calc_eps_growth_rate(previous2_row.revised_eps, previous_row.revised_eps) if previous2_row is not None else None
    )

    row_by_year = {row.year: row for row in growth_rows}
    cagr_start_row = row_by_year.get(current_row.year - 3)

    return GrowthPhaseInput(
        sales_growth_current=sales_growth_current,
        op_growth_current=op_growth_current,
        eps_growth_current=eps_growth_current,
        sales_growth_previous=sales_growth_previous,
        op_growth_previous=op_growth_previous,
        eps_growth_previous=eps_growth_previous,
        sales_cagr_3y=calc_cagr(cagr_start_row.sales if cagr_start_row else None, current_row.sales, 3),
        op_cagr_3y=calc_cagr(cagr_start_row.operating_profit if cagr_start_row else None, current_row.operating_profit, 3),
        eps_cagr_3y=calc_cagr(cagr_start_row.revised_eps if cagr_start_row else None, current_row.revised_eps, 3),
        previous_op=previous_row.operating_profit,
        current_op=current_row.operating_profit,
        previous_eps=previous_row.revised_eps,
        current_eps=current_row.revised_eps,
    )


def classify_growth_phase_from_rows(rows: list[KabutanForecastRow] | tuple[KabutanForecastRow, ...]) -> GrowthPhase:
    return classify_growth_phase(build_growth_phase_input(rows))


def _calc_growth_rate(previous_value: int | float | None, current_value: int | float | None) -> float | None:
    if previous_value is None or current_value is None or previous_value == 0:
        return None
    return ((float(current_value) - float(previous_value)) / float(previous_value)) * 100


def _all_present(*values: float | int | None) -> bool:
    return all(value is not None for value in values)


def _any_cagr_at_least(data: GrowthPhaseInput, threshold: float) -> bool:
    values = (data.sales_cagr_3y, data.op_cagr_3y, data.eps_cagr_3y)
    return any(value is not None and value >= threshold for value in values)


def _all_cagr_below(data: GrowthPhaseInput, threshold: float) -> bool:
    values = (data.sales_cagr_3y, data.op_cagr_3y, data.eps_cagr_3y)
    return all(value is not None and value < threshold for value in values)


def _is_recovery_phase(data: GrowthPhaseInput) -> bool:
    had_decline_or_loss = (
        (data.op_growth_previous is not None and data.op_growth_previous < 0)
        or (data.eps_growth_previous is not None and data.eps_growth_previous < 0)
        or (data.previous_op is not None and data.previous_op < 0)
        or (data.previous_eps is not None and data.previous_eps < 0)
    )
    sales_recovered = data.sales_growth_current is not None and data.sales_growth_current > 0
    op_recovered = (
        data.previous_op is not None
        and data.current_op is not None
        and data.previous_op < 0
        and data.current_op > 0
    ) or (data.op_growth_current is not None and data.op_growth_current >= 20)
    eps_recovered = (
        data.previous_eps is not None
        and data.current_eps is not None
        and data.previous_eps < 0
        and data.current_eps > 0
    ) or (data.eps_growth_current is not None and data.eps_growth_current >= 20)
    return had_decline_or_loss and sales_recovered and op_recovered and eps_recovered


def _is_growth_reaccelerating(data: GrowthPhaseInput) -> bool:
    sales_improved = (
        _all_present(data.sales_growth_current, data.sales_growth_previous)
        and data.sales_growth_current - data.sales_growth_previous >= 5
    )
    op_improved = (
        _all_present(data.op_growth_current, data.op_growth_previous)
        and data.op_growth_current - data.op_growth_previous >= 10
    )
    eps_improved = (
        _all_present(data.eps_growth_current, data.eps_growth_previous)
        and data.eps_growth_current - data.eps_growth_previous >= 10
    )
    return (sales_improved or op_improved or eps_improved) and _any_cagr_at_least(data, 5)


def _is_high_growth_after_slowdown(data: GrowthPhaseInput) -> bool:
    sales_slowed = (
        _all_present(data.sales_growth_current, data.sales_growth_previous)
        and data.sales_growth_current >= 10
        and data.sales_growth_current - data.sales_growth_previous <= -5
    )
    op_slowed = (
        _all_present(data.op_growth_current, data.op_growth_previous)
        and data.op_growth_current >= 15
        and data.op_growth_current - data.op_growth_previous <= -10
    )
    eps_slowed = (
        _all_present(data.eps_growth_current, data.eps_growth_previous)
        and data.eps_growth_current >= 15
        and data.eps_growth_current - data.eps_growth_previous <= -10
    )
    return (sales_slowed or op_slowed or eps_slowed) and _any_cagr_at_least(data, 10)


def _is_high_growth(data: GrowthPhaseInput) -> bool:
    return (
        _all_present(data.sales_growth_current, data.op_growth_current, data.eps_growth_current)
        and data.sales_growth_current >= 10
        and data.op_growth_current >= 15
        and data.eps_growth_current >= 15
        and _any_cagr_at_least(data, 10)
    )


def _is_profit_improving(data: GrowthPhaseInput) -> bool:
    return (
        _all_present(data.sales_growth_current, data.op_growth_current, data.eps_growth_current)
        and data.sales_growth_current < 5
        and data.op_growth_current >= 10
        and data.eps_growth_current >= 10
        and _any_cagr_at_least(data, 5)
    )


def _is_low_growth(data: GrowthPhaseInput) -> bool:
    return (
        _all_present(data.sales_growth_current, data.op_growth_current, data.eps_growth_current)
        and data.sales_growth_current < 5
        and data.op_growth_current < 5
        and data.eps_growth_current < 5
        and _all_cagr_below(data, 5)
    )


__all__ = [
    "GrowthPhase",
    "GrowthPhaseInput",
    "build_growth_phase_input",
    "classify_growth_phase",
    "classify_growth_phase_from_rows",
]
