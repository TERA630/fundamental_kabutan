"""Domain policy for quarterly year-over-year growth calculations."""

from __future__ import annotations

from app.domain.models.quarterly_financials import QuarterlyActual
from app.domain.models.quarterly_financials import GrowthMetricKind, Quarter, QuarterlyGrowthMetrics, YoYMetric, YoYStatus


def resolve_quarter_from_fiscal_end_month(*, quarter_end_month: int | None, fiscal_end_month: int | None) -> Quarter | None:
    if quarter_end_month is None or fiscal_end_month is None:
        return None
    delta = (quarter_end_month - fiscal_end_month) % 12
    mapping = {3: Quarter.Q1, 6: Quarter.Q2, 9: Quarter.Q3, 0: Quarter.Q4}
    return mapping.get(delta)


def assign_quarter(*, row: QuarterlyActual, fiscal_end_month: int | None) -> QuarterlyActual:
    quarter = resolve_quarter_from_fiscal_end_month(
        quarter_end_month=row.quarter_end_month,
        fiscal_end_month=fiscal_end_month,
    )
    return QuarterlyActual(
        ticker=row.ticker,
        fiscal_year=row.fiscal_year,
        quarter=quarter,
        quarter_end_month=row.quarter_end_month,
        sales=row.sales,
        ordinary_profit=row.ordinary_profit,
        operating_profit=row.operating_profit,
        revised_eps=row.revised_eps,
        operating_margin=row.operating_margin,
    )


def find_prior_same_quarter(*, rows: list[QuarterlyActual], current: QuarterlyActual) -> QuarterlyActual | None:
    if current.quarter is None:
        return None
    for row in rows:
        if row.ticker != current.ticker:
            continue
        if row.fiscal_year != current.fiscal_year - 1:
            continue
        if row.quarter != current.quarter:
            continue
        return row
    return None


def calc_yoy_change(
    previous_value: float | int | None,
    current_value: float | int | None,
    *,
    metric_kind: GrowthMetricKind,
) -> YoYMetric:
    if previous_value is None or current_value is None:
        return YoYMetric(status=YoYStatus.NA, value_pct=None)
    previous = float(previous_value)
    current = float(current_value)
    if previous == 0:
        return YoYMetric(status=YoYStatus.NA, value_pct=None)

    value_pct = ((current - previous) / abs(previous)) * 100
    if metric_kind in (GrowthMetricKind.OPERATING_PROFIT, GrowthMetricKind.REVISED_EPS) and previous < 0 < current:
        return YoYMetric(status=YoYStatus.TURNAROUND_TO_PROFIT, value_pct=value_pct)
    return YoYMetric(status=YoYStatus.OK, value_pct=value_pct)


def resolve_operating_margin(
    operating_margin_from_html: float | None,
    *,
    sales: int | None,
    operating_profit: int | None,
) -> float | None:
    if operating_margin_from_html is not None:
        return operating_margin_from_html
    if sales is None or operating_profit is None or sales == 0:
        return None
    return (operating_profit / sales) * 100


def _build_na_growth_metrics() -> QuarterlyGrowthMetrics:
    na = YoYMetric(status=YoYStatus.NA, value_pct=None)
    return QuarterlyGrowthMetrics(
        operating_profit_yoy=na,
        operating_margin_yoy=na,
        revised_eps_yoy=na,
    )


def build_quarterly_growth_metrics(*, previous: QuarterlyActual | None, current: QuarterlyActual) -> QuarterlyGrowthMetrics:
    if previous is None:
        return _build_na_growth_metrics()

    previous_margin = resolve_operating_margin(
        previous.operating_margin,
        sales=previous.sales,
        operating_profit=previous.operating_profit,
    )
    current_margin = resolve_operating_margin(
        current.operating_margin,
        sales=current.sales,
        operating_profit=current.operating_profit,
    )

    return QuarterlyGrowthMetrics(
        operating_profit_yoy=calc_yoy_change(
            previous_value=previous.operating_profit,
            current_value=current.operating_profit,
            metric_kind=GrowthMetricKind.OPERATING_PROFIT,
        ),
        operating_margin_yoy=calc_yoy_change(
            previous_value=previous_margin,
            current_value=current_margin,
            metric_kind=GrowthMetricKind.OPERATING_MARGIN,
        ),
        revised_eps_yoy=calc_yoy_change(
            previous_value=previous.revised_eps,
            current_value=current.revised_eps,
            metric_kind=GrowthMetricKind.REVISED_EPS,
        ),
    )


__all__ = [
    "assign_quarter",
    "build_quarterly_growth_metrics",
    "calc_yoy_change",
    "find_prior_same_quarter",
    "resolve_operating_margin",
    "resolve_quarter_from_fiscal_end_month",
]
