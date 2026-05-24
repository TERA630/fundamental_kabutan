from app.domain.models.kabutan_forecast import KabutanForecastRow
from app.domain.policies.growth_metrics import (
    calc_eps_growth_rate,
    calc_operating_growth_rate,
    calc_cagr,
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
