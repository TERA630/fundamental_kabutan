from app.domain.models.kabutan_forecast import KabutanForecastRow
from app.domain.policies.growth_metrics import (
    calc_eps_growth_rate,
    calc_operating_growth_rate,
    calc_cagr,
)
from app.domain.policies.growth_phase import (
    GrowthPhaseInput,
    build_growth_phase_input,
    classify_growth_phase,
    classify_growth_phase_from_rows,
)
from app.domain.policies.growth_rows import build_growth_rows


def test_build_growth_rows_skips_same_year_forecast_after_actual():
    rows = [
        KabutanForecastRow("2025.03", 2025, 3, "実績", 1000, 100, 90, 80, 10.0, 2.0),
        KabutanForecastRow("2026.03", 2026, 3, "実績", 1200, 130, 120, 110, 12.0, 2.5),
        KabutanForecastRow("2026.03", 2026, 3, "予想", 1250, 140, 130, 115, 13.0, 2.5),
        KabutanForecastRow("2027.03", 2027, 3, "予想", 1300, 150, 140, 120, 14.0, 3.0),
    ]
    targets = build_growth_rows(rows)
    assert [(r.year, r.section) for r in targets] == [(2025, "実績"), (2026, "実績"), (2027, "予想")]


def test_growth_metric_formulas():
    assert calc_operating_growth_rate(100, 120) == 20.0
    assert calc_eps_growth_rate(10.0, 12.0) == 20.0


def test_eps_growth_rate_zero_base_is_na():
    assert calc_eps_growth_rate(0.0, 12.0) is None


def test_calc_cagr_3y_positive():
    result = calc_cagr(100, 133.1, 3)
    assert result is not None
    assert round(result, 1) == 10.0


def test_calc_cagr_returns_none_for_negative_or_zero_base():
    assert calc_cagr(0, 120, 3) is None
    assert calc_cagr(-100, 120, 3) is None
    assert calc_cagr(100, -120, 3) is None


def test_calc_cagr_returns_none_for_missing_values():
    assert calc_cagr(None, 120, 3) is None
    assert calc_cagr(100, None, 3) is None


def test_classify_growth_phase_recovery_from_loss():
    phase = classify_growth_phase(
        GrowthPhaseInput(
            sales_growth_current=3.0,
            op_growth_current=None,
            eps_growth_current=None,
            op_growth_previous=-10.0,
            previous_op=-10,
            current_op=5,
            previous_eps=-2.0,
            current_eps=1.0,
        )
    )

    assert phase == "業績回復途上"


def test_classify_growth_phase_recovery_from_decline_with_twenty_percent_improvement():
    phase = classify_growth_phase(
        GrowthPhaseInput(
            sales_growth_current=1.0,
            op_growth_current=20.0,
            eps_growth_current=25.0,
            op_growth_previous=-1.0,
            previous_op=100,
            current_op=120,
            previous_eps=10.0,
            current_eps=12.5,
        )
    )

    assert phase == "業績回復途上"


def test_classify_growth_phase_reaccelerating():
    phase = classify_growth_phase(
        GrowthPhaseInput(
            sales_growth_current=9.0,
            sales_growth_previous=3.0,
            sales_cagr_3y=6.0,
        )
    )

    assert phase == "成長再加速"


def test_classify_growth_phase_high_growth_after_slowdown():
    phase = classify_growth_phase(
        GrowthPhaseInput(
            sales_growth_current=12.0,
            sales_growth_previous=20.0,
            sales_cagr_3y=11.0,
        )
    )

    assert phase == "高成長鈍化後"


def test_classify_growth_phase_high_growth():
    phase = classify_growth_phase(
        GrowthPhaseInput(
            sales_growth_current=12.0,
            op_growth_current=18.0,
            eps_growth_current=16.0,
            sales_cagr_3y=10.0,
        )
    )

    assert phase == "高成長中"


def test_classify_growth_phase_profit_improving():
    phase = classify_growth_phase(
        GrowthPhaseInput(
            sales_growth_current=4.0,
            op_growth_current=12.0,
            eps_growth_current=11.0,
            sales_cagr_3y=5.0,
        )
    )

    assert phase == "利益改善型"


def test_classify_growth_phase_low_growth():
    phase = classify_growth_phase(
        GrowthPhaseInput(
            sales_growth_current=4.0,
            op_growth_current=3.0,
            eps_growth_current=2.0,
            sales_cagr_3y=4.0,
            op_cagr_3y=3.0,
            eps_cagr_3y=2.0,
        )
    )

    assert phase == "低成長"


def test_classify_growth_phase_falls_back_to_stable_growth():
    assert classify_growth_phase(GrowthPhaseInput()) == "安定成長"


def test_build_growth_phase_input_from_rows_uses_latest_growth_row():
    rows = [
        KabutanForecastRow("2024.03", 2024, 3, "実績", 100, 10, 9, 8, 10.0, 2.0),
        KabutanForecastRow("2025.03", 2025, 3, "実績", 103, 9, 8, 7, 9.0, 2.0),
        KabutanForecastRow("2026.03", 2026, 3, "予想", 110, 12, 11, 10, 12.0, 2.0),
        KabutanForecastRow("2027.03", 2027, 3, "予想", 130, 18, 15, 13, 18.0, 2.0),
    ]

    data = build_growth_phase_input(rows)

    assert round(data.sales_growth_current, 1) == 18.2
    assert round(data.op_growth_previous, 1) == 33.3
    assert round(data.eps_cagr_3y, 1) == 21.6
    assert classify_growth_phase_from_rows(rows) == "成長再加速"
