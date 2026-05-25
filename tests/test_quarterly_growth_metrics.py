from __future__ import annotations

from app.domain.models.quarterly_financials import GrowthMetricKind, Quarter, QuarterlyActual, YoYStatus
from app.domain.policies.quarterly_growth_metrics import (
    build_quarterly_growth_metrics,
    calc_yoy_change,
    resolve_operating_margin,
    resolve_quarter_from_fiscal_end_month,
)


def test_calc_yoy_change_returns_na_when_previous_zero() -> None:
    result = calc_yoy_change(previous_value=0, current_value=100, metric_kind=GrowthMetricKind.OPERATING_PROFIT)
    assert result.status == YoYStatus.NA
    assert result.value_pct is None


def test_calc_yoy_change_uses_abs_denominator() -> None:
    result = calc_yoy_change(previous_value=-50, current_value=-25, metric_kind=GrowthMetricKind.OPERATING_PROFIT)
    assert result.status == YoYStatus.OK
    assert result.value_pct == 50.0


def test_calc_yoy_change_marks_turnaround_only_for_op_and_eps() -> None:
    op = calc_yoy_change(previous_value=-100, current_value=10, metric_kind=GrowthMetricKind.OPERATING_PROFIT)
    eps = calc_yoy_change(previous_value=-1.2, current_value=0.1, metric_kind=GrowthMetricKind.REVISED_EPS)
    margin = calc_yoy_change(previous_value=-2.0, current_value=1.0, metric_kind=GrowthMetricKind.OPERATING_MARGIN)

    assert op.status == YoYStatus.TURNAROUND_TO_PROFIT
    assert eps.status == YoYStatus.TURNAROUND_TO_PROFIT
    assert margin.status == YoYStatus.OK


def test_resolve_operating_margin_prefers_html_and_fallbacks_to_recompute() -> None:
    assert resolve_operating_margin(operating_margin_from_html=12.3, sales=1000, operating_profit=100) == 12.3
    assert resolve_operating_margin(operating_margin_from_html=None, sales=1000, operating_profit=120) == 12.0


def test_resolve_operating_margin_returns_none_when_sales_missing_or_zero() -> None:
    assert resolve_operating_margin(operating_margin_from_html=None, sales=None, operating_profit=120) is None
    assert resolve_operating_margin(operating_margin_from_html=None, sales=0, operating_profit=120) is None


def test_build_quarterly_growth_metrics() -> None:
    previous = QuarterlyActual(
        ticker="1234",
        fiscal_year=2025,
        quarter=Quarter.Q1,
        quarter_end_month=6,
        sales=1_000,
        ordinary_profit=100,
        operating_profit=-50,
        revised_eps=-10.0,
        operating_margin=5.0,
    )
    current = QuarterlyActual(
        ticker="1234",
        fiscal_year=2026,
        quarter=Quarter.Q1,
        quarter_end_month=6,
        sales=1_100,
        ordinary_profit=120,
        operating_profit=25,
        revised_eps=3.0,
        operating_margin=7.0,
    )

    metrics = build_quarterly_growth_metrics(previous=previous, current=current)

    assert metrics.operating_profit_yoy.status == YoYStatus.TURNAROUND_TO_PROFIT
    assert metrics.revised_eps_yoy.status == YoYStatus.TURNAROUND_TO_PROFIT
    assert metrics.operating_margin_yoy.status == YoYStatus.OK


def test_build_quarterly_growth_metrics_returns_na_when_previous_missing() -> None:
    current = QuarterlyActual(
        ticker="1234",
        fiscal_year=2026,
        quarter=Quarter.Q1,
        quarter_end_month=6,
        sales=1_100,
        ordinary_profit=120,
        operating_profit=25,
        revised_eps=3.0,
        operating_margin=7.0,
    )

    metrics = build_quarterly_growth_metrics(previous=None, current=current)

    assert metrics.operating_profit_yoy.status == YoYStatus.NA
    assert metrics.operating_margin_yoy.status == YoYStatus.NA
    assert metrics.revised_eps_yoy.status == YoYStatus.NA


def test_build_quarterly_growth_metrics_recomputes_margin_when_html_margin_is_missing() -> None:
    previous = QuarterlyActual(
        ticker="1234",
        fiscal_year=2025,
        quarter=Quarter.Q1,
        quarter_end_month=6,
        sales=1_000,
        ordinary_profit=100,
        operating_profit=100,
        revised_eps=10.0,
        operating_margin=None,
    )
    current = QuarterlyActual(
        ticker="1234",
        fiscal_year=2026,
        quarter=Quarter.Q1,
        quarter_end_month=6,
        sales=2_000,
        ordinary_profit=140,
        operating_profit=260,
        revised_eps=14.0,
        operating_margin=None,
    )

    metrics = build_quarterly_growth_metrics(previous=previous, current=current)

    assert metrics.operating_margin_yoy.status == YoYStatus.OK
    assert metrics.operating_margin_yoy.value_pct == 30.0


def test_resolve_quarter_from_fiscal_end_month_supports_non_march_cycles() -> None:
    assert resolve_quarter_from_fiscal_end_month(quarter_end_month=12, fiscal_end_month=9) == Quarter.Q1
    assert resolve_quarter_from_fiscal_end_month(quarter_end_month=3, fiscal_end_month=9) == Quarter.Q2
    assert resolve_quarter_from_fiscal_end_month(quarter_end_month=6, fiscal_end_month=9) == Quarter.Q3
    assert resolve_quarter_from_fiscal_end_month(quarter_end_month=9, fiscal_end_month=9) == Quarter.Q4


def test_resolve_quarter_from_fiscal_end_month_returns_none_when_unresolvable() -> None:
    assert resolve_quarter_from_fiscal_end_month(quarter_end_month=None, fiscal_end_month=3) is None
    assert resolve_quarter_from_fiscal_end_month(quarter_end_month=8, fiscal_end_month=3) is None
