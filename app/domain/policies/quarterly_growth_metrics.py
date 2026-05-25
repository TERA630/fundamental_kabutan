"""Domain policy for quarterly year-over-year growth calculations."""

from __future__ import annotations

from app.domain.models.quarterly_financials import GrowthMetricKind, QuarterlyGrowthMetrics, YoYMetric, YoYStatus


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


def build_quarterly_growth_metrics(*, previous, current) -> QuarterlyGrowthMetrics:
    return QuarterlyGrowthMetrics(
        operating_profit_yoy=calc_yoy_change(
            previous_value=previous.operating_profit,
            current_value=current.operating_profit,
            metric_kind=GrowthMetricKind.OPERATING_PROFIT,
        ),
        operating_margin_yoy=calc_yoy_change(
            previous_value=previous.operating_margin,
            current_value=current.operating_margin,
            metric_kind=GrowthMetricKind.OPERATING_MARGIN,
        ),
        revised_eps_yoy=calc_yoy_change(
            previous_value=previous.revised_eps,
            current_value=current.revised_eps,
            metric_kind=GrowthMetricKind.REVISED_EPS,
        ),
    )


__all__ = ["build_quarterly_growth_metrics", "calc_yoy_change", "resolve_operating_margin"]
