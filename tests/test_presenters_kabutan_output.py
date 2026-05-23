from app.domain.models.kabutan_forecast import KabutanForecastPair, KabutanForecastRow
from app.presenters import build_kabutan_forecast_output


def test_build_kabutan_forecast_output_appends_section():
    base = "base output"
    pair = KabutanForecastPair(
        previous2_actual=None,
        previous_actual=KabutanForecastRow("2025.03", 2025, 3, "実績", 1000, 100, 90, 80),
        current_actual=None,
        current_forecast=KabutanForecastRow("2026.03", 2026, 3, "予想", 1200, 130, 120, 110),
        next_forecast=KabutanForecastRow("2027.03", 2027, 3, "予想", 1350, 150, 140, 120),
    )

    text = build_kabutan_forecast_output(base, pair, "html", None)

    assert "■株探 通期業績推移" in text
    assert "2025年" in text
    assert "2026年(予)" in text
    assert "2027年(予)" in text

def test_build_kabutan_forecast_output_renders_na_rows_when_none():
    text = build_kabutan_forecast_output("base output", None, "none", "HTML解析に失敗")
    assert "■株探 通期業績推移" in text
    assert "株探ソース: 取得不可 (HTML解析に失敗)" in text
    assert "データーが取得できません" in text
    assert "2025年" not in text
    assert "予想チェーン" not in text


def test_build_kabutan_forecast_output_growth_skips_same_year_actual_to_forecast():
    base = "base output"
    pair = KabutanForecastPair(
        previous2_actual=KabutanForecastRow("2024.03", 2024, 3, "実績", 900, 90, 80, 70),
        previous_actual=KabutanForecastRow("2025.03", 2025, 3, "実績", 1000, 100, 90, 80),
        current_actual=KabutanForecastRow("2026.03", 2026, 3, "実績", 1200, 130, 120, 110),
        current_forecast=KabutanForecastRow("2026.03", 2026, 3, "予想", 1250, 140, 130, 115),
        next_forecast=KabutanForecastRow("2027.03", 2027, 3, "予想", 1350, 150, 140, 120),
    )
    text = build_kabutan_forecast_output(base, pair, "html", None)
    # 成長率は2024->2025->2026実->2027予で計算し、2026予は成長率行に含めない
    assert "2026年(予)" not in text.split("前年度営業利益成長率(%)", 1)[1]
    assert "2027年(予)" in text


def test_build_kabutan_forecast_output_uses_all_rows_when_available():
    base = "base output"
    pair = KabutanForecastPair(
        previous2_actual=None,
        previous_actual=KabutanForecastRow("2025.03", 2025, 3, "実績", 1000, 100, 90, 80),
        current_actual=None,
        current_forecast=KabutanForecastRow("2026.03", 2026, 3, "予想", 1200, 130, 120, 110),
        next_forecast=KabutanForecastRow("2027.03", 2027, 3, "予想", 1350, 150, 140, 120),
        all_rows=(
            KabutanForecastRow("2023.03", 2023, 3, "実績", 800, 70, 60, 50),
            KabutanForecastRow("2024.03", 2024, 3, "実績", 900, 80, 70, 60),
            KabutanForecastRow("2025.03", 2025, 3, "実績", 1000, 100, 90, 80),
            KabutanForecastRow("2026.03", 2026, 3, "実績", 1200, 130, 120, 110),
            KabutanForecastRow("2027.03", 2027, 3, "予想", 1350, 150, 140, 120),
        ),
    )
    text = build_kabutan_forecast_output(base, pair, "html", None)
    assert "2023年" in text
    assert "2024年" in text
    assert "2027年(予)" in text
