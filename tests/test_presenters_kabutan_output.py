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
    assert "■キャッシュフロー" in text
    assert "N/A" in text


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
    assert "2026年(予)" not in text.split("営業利益成長率", 1)[1]
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


def test_build_kabutan_forecast_output_builds_cashflow_two_tables_and_negative_yield():
    base = "base output"
    pair = KabutanForecastPair(
        previous2_actual=KabutanForecastRow("2022.03", 2022, 3, "実績", 800, 80, 70, 60),
        previous_actual=KabutanForecastRow("2023.03", 2023, 3, "実績", 900, 90, 80, 40),
        current_actual=KabutanForecastRow("2024.03", 2024, 3, "実績", 1000, 110, 100, 50),
        current_forecast=KabutanForecastRow("2024.03", 2024, 3, "予想", 1010, 112, 101, 51),
        next_forecast=None,
    )

    from app.domain.models.kabutan_cashflow import KabutanCashflowRow

    text = build_kabutan_forecast_output(
        base,
        pair,
        "html",
        None,
        (
            KabutanCashflowRow("2022.03", 2022, 3, 100, 140, -40, 10, 300),
            KabutanCashflowRow("2023.03", 2023, 3, -50, 120, -170, 20, 280),
            KabutanCashflowRow("2024.03", 2024, 3, 80, 150, -70, 30, 350),
        ),
        10_000_000_000.0,
    )

    assert "[A] CF実績（百万円）" in text
    assert "年度 | フリーCF | 営業CF | 投資CF | 財務CF | 現金等残高" in text
    assert "[B] 指標（%）" in text
    assert "年度 | 営業CFマージン | Cash conversion | FCFマージン | FCF Yield" in text
    assert "2022 | 100 | 140 | -40 | 10 | 300" in text
    assert "2023 | -50 | 120 | -170 | 20 | 280" in text
    assert "2024 | 80 | 150 | -70 | 30 | 350" in text
    assert "2023 | 13.3% | 300.0% | -5.6% | -0.5%" in text


def test_build_kabutan_forecast_output_uses_operating_plus_investing_when_free_cf_missing():
    base = "base output"
    pair = KabutanForecastPair(
        previous2_actual=None,
        previous_actual=KabutanForecastRow("2023.03", 2023, 3, "実績", 900, 90, 80, 40),
        current_actual=KabutanForecastRow("2024.03", 2024, 3, "実績", 1000, 110, 100, 50),
        current_forecast=KabutanForecastRow("2024.03", 2024, 3, "予想", 1010, 112, 101, 51),
        next_forecast=None,
    )

    from app.domain.models.kabutan_cashflow import KabutanCashflowRow

    text = build_kabutan_forecast_output(
        base,
        pair,
        "html",
        None,
        (KabutanCashflowRow("2024.03", 2024, 3, None, 150, -70, 30, 350),),
        10_000_000_000.0,
    )

    assert "2024 | 15.0% | 300.0% | 8.0% | 0.8%" in text
