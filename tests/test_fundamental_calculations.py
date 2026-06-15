from app.domain.models.kabutan_forecast import KabutanForecastPair, KabutanForecastRow
from app.domain.usecases import fundamental_calculations as calculations


def test_resolve_fiscal_end_month_from_forecast_pair_uses_latest_row_month():
    pair = KabutanForecastPair(
        previous2_actual=None,
        previous_actual=None,
        current_actual=None,
        current_forecast=KabutanForecastRow("2026.06", 2026, 6, "予想", 1200, 120, 100, 90),
        next_forecast=KabutanForecastRow("2027.06", 2027, 6, "予想", 1300, 130, 110, 95),
        all_rows=(
            KabutanForecastRow("2025.06", 2025, 6, "実績", 1000, 100, 90, 80),
            KabutanForecastRow("2026.06", 2026, 6, "予想", 1200, 120, 100, 90),
        ),
    )

    assert calculations.resolve_fiscal_end_month_from_forecast_pair(pair) == 6


def test_build_per_and_roic_levels_from_plain_scoring_object():
    scoring_input = type("ScoringInput", (), {"per": 31.0, "roic": 12.0})()

    assert calculations.build_per_level(cf_scoring_input=scoring_input, industry="Semiconductors") == "高PER"
    assert calculations.build_roic_level(scoring_input) == "高ROIC"
