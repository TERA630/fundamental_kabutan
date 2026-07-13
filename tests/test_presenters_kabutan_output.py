from app.domain.models.kabutan_forecast import KabutanForecastPair, KabutanForecastRow
from app.domain.models.financial_snapshot import FinancialMetricInputRow
from app.presentation.kabutan_output import build_kabutan_forecast_output
from app.domain.builders.kabutan_output import build_kabutan_forecast_sections
from app.domain.models.display_sections import (
    CashflowTimelineSection,
    FinancialMetricsSection,
    ForecastTableSection,
    GrowthTimelineSection,
    QuarterlyMetricsSection,
)


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
    assert "2025/03" in text
    assert "2026/03(予)" in text
    assert "2027/03(予)" in text


def test_build_kabutan_forecast_sections_builds_display_dtos():
    pair = KabutanForecastPair(
        previous2_actual=None,
        previous_actual=KabutanForecastRow("2025.03", 2025, 3, "実績", 1000, 100, 90, 80),
        current_actual=None,
        current_forecast=KabutanForecastRow("2026.03", 2026, 3, "予想", 1200, 130, 120, 110),
        next_forecast=None,
    )

    sections = build_kabutan_forecast_sections(pair, "html", None)

    assert isinstance(sections.sections[0], ForecastTableSection)
    assert isinstance(sections.sections[1], GrowthTimelineSection)
    assert isinstance(sections.sections[2], CashflowTimelineSection)
    assert isinstance(sections.sections[3], FinancialMetricsSection)
    assert isinstance(sections.sections[4], QuarterlyMetricsSection)


def test_build_kabutan_forecast_output_renders_na_rows_when_none():
    text = build_kabutan_forecast_output("base output", None, "none", "HTML解析に失敗")
    assert "■株探 通期業績推移" in text
    assert "株探ソース: 取得不可 (HTML解析に失敗)" in text
    assert "データーが取得できません" in text
    assert "2025/03" not in text
    assert "予想チェーン" not in text
    assert "■キャッシュフロー" in text
    assert "N/A" in text


def test_build_kabutan_forecast_output_logs_missing_non_score_blocks(caplog):
    caplog.set_level("INFO")

    build_kabutan_forecast_output("base output", None, "none", "HTML解析に失敗")

    assert "取得不可: 株探通期業績推移 (値欠損)" in caplog.text
    assert "取得不可: キャッシュフロー (値欠損)" in caplog.text
    assert "取得不可: 財務ブロック (値欠損)" in caplog.text
    assert "取得不可: 四半期トレンド (値欠損)" in caplog.text


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
    assert "EPS成長率" not in text
    assert "営業利益成長率" not in text
    assert "2027/03(予)" in text


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
    assert "2023/03" in text
    assert "2024/03" in text
    assert "2027/03(予)" in text


def test_build_kabutan_forecast_output_builds_cashflow_intention_table():
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

    assert "年度 | 営業CF | FCF | 投資積極性 | 現金残高" in text
    assert "Cash conversion" not in text
    assert "2022 | 140 | 100 | 28.6% | 300" in text
    assert "2023 | 120 | -50 | 141.7% | 280" in text
    assert "2024 | 150 | 80 | 46.7% | 350" in text


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

    assert "2024 | 150 | 80 | 46.7% | 350" in text


def test_build_kabutan_forecast_output_keeps_negative_operating_cf_sign_for_investment_aggressiveness():
    base = "base output"
    pair = KabutanForecastPair(
        previous2_actual=None,
        previous_actual=KabutanForecastRow("2024.03", 2024, 3, "実績", 1000, 110, 100, 50),
        current_actual=None,
        current_forecast=KabutanForecastRow("2024.03", 2024, 3, "予想", 1010, 112, 101, 51),
        next_forecast=None,
    )

    from app.domain.models.kabutan_cashflow import KabutanCashflowRow

    text = build_kabutan_forecast_output(
        base,
        pair,
        "html",
        None,
        (KabutanCashflowRow("2024.03", 2024, 3, -150, -100, -50, 30, 350),),
        10_000_000_000.0,
    )

    assert "2024 | -100 | -150 | -50.0% | 350" in text


def test_build_kabutan_forecast_output_appends_financial_block_with_formats():
    base = "base output"
    text = build_kabutan_forecast_output(
        base,
        None,
        "none",
        None,
        (),
        None,
        (
            FinancialMetricInputRow(
                year=2022,
                net_income=120,
                equity=600,
                operating_profit=100,
                interest_bearing_debt=100,
                bps=1500.0,
                price=3000.0,
            ),
            FinancialMetricInputRow(
                year=2023,
                net_income=None,
                equity=700,
                operating_profit=120,
                interest_bearing_debt=140,
                bps=0.0,
                price=3200.0,
            ),
        ),
    )

    assert "■財務ブロック" in text
    assert "ROE(%)|ROIC(%)|PBR|" in text
    assert "2022年　20.0%|10.0%|2.00倍" in text
    assert "2023年　N/A|10.0%|N/A" in text


def test_build_kabutan_forecast_output_financial_block_na_when_empty():
    text = build_kabutan_forecast_output("base", None, "none", None)
    assert "■財務ブロック" in text
    assert "ROE(%)|ROIC(%)|PBR|" in text
    assert "N/A" in text


def test_build_kabutan_output_summarizes_growth_with_cagr_lines():
    from app.presentation.kabutan_output import build_kabutan_forecast_output
    from app.domain.models.kabutan_forecast import KabutanForecastPair, KabutanForecastRow

    rows = (
        KabutanForecastRow("2023.03", 2023, 3, "実績", 1000, 100, 90, 80, 100.0, 20.0),
        KabutanForecastRow("2024.03", 2024, 3, "実績", 1100, 110, 100, 90, 110.0, 22.0),
        KabutanForecastRow("2025.03", 2025, 3, "実績", 1200, 121, 110, 95, 121.0, 24.0),
        KabutanForecastRow("2026.03", 2026, 3, "予想", 1300, 133, 120, 100, 133.0, 26.0),
    )
    pair = KabutanForecastPair(
        previous2_actual=rows[0],
        previous_actual=rows[1],
        current_actual=rows[2],
        current_forecast=rows[3],
        next_forecast=None,
        all_rows=rows,
    )

    out = build_kabutan_forecast_output("base", pair, "html", None)

    assert "売上CAGR 2023→2026" in out
    assert "営業利益CAGR 2023→2026" in out
    assert "EPS CAGR 2023→2026" in out
    assert "EPS成長率" not in out
    assert "営業利益成長率" not in out


def test_build_kabutan_output_uses_latest_complete_growth_year_for_cagr():
    rows = (
        KabutanForecastRow("2023.03", 2023, 3, "実績", 92242, 49891, 51283, 36296, 1496.6, 300.0),
        KabutanForecastRow("2024.03", 2024, 3, "実績", 96729, 49501, 51929, 36964, 1524.1, 300.0),
        KabutanForecastRow("2025.03", 2025, 3, "実績", 105915, 54978, 56101, 39866, 1643.8, 350.0),
        KabutanForecastRow("2026.03", 2026, 3, "実績", 116929, 59576, 63576, 44519, 1835.6, 550.0),
        KabutanForecastRow("2027.03", 2027, 3, "予想", None, None, None, None, None, 550.0),
    )
    pair = KabutanForecastPair(
        previous2_actual=rows[1],
        previous_actual=rows[2],
        current_actual=rows[3],
        current_forecast=None,
        next_forecast=rows[4],
        all_rows=rows,
    )

    out = build_kabutan_forecast_output("base", pair, "html", None)

    assert "2027/03(予)" in out
    assert "売上CAGR 2023→2026" in out
    assert "営業利益CAGR 2023→2026" in out
    assert "EPS CAGR 2023→2026" in out
    assert "2024→2027" not in out


from app.domain.models.quarterly_financials import Quarter, QuarterlyMetricRow


def test_build_kabutan_forecast_output_includes_quarterly_block():
    text = build_kabutan_forecast_output(
        "base",
        None,
        "none",
        None,
        (),
        None,
        (),
        (
            QuarterlyMetricRow(2025, Quarter.Q1, 3, 1000, 100, 90, 80, 10.0, None, None, 10.0, None),
            QuarterlyMetricRow(2026, Quarter.Q1, 3, 1200, 120, 100, 90, 12.0, 20.0, 20.0, 10.0, 20.0),
        ),
    )
    assert "■四半期トレンド" in text
    assert "売上|営業利益率|昨年同期比|修正一株益" in text
    assert "2025.3" in text
    assert "2026.3" in text


def test_build_kabutan_forecast_output_quarterly_trend_snapshot():
    text = build_kabutan_forecast_output(
        "base",
        None,
        "none",
        None,
        (),
        None,
        (),
        (
            QuarterlyMetricRow(2025, Quarter.Q1, 3, 1000, 100, 90, 80, 10.0, None, None, 10.0, -10.0),
            QuarterlyMetricRow(2025, Quarter.Q2, 6, None, None, 95, None, None, 12.3, None, None),
        ),
    )
    expected_lines = [
        "■四半期トレンド",
        "　　　売上|営業利益率|昨年同期比|修正一株益",
        "2025.3　10.0億|10.0%|-10%|10.0円",
        "2025.6　N/A|N/A||N/A",
    ]
    for line in expected_lines:
        assert line in text


def test_build_kabutan_forecast_output_quarterly_trend_all_yoy_blank():
    text = build_kabutan_forecast_output(
        "base",
        None,
        "none",
        None,
        (),
        None,
        (),
        (
            QuarterlyMetricRow(2025, Quarter.Q1, 3, 1000, 100, 90, 80, 10.0, None, None, 10.0),
            QuarterlyMetricRow(2025, Quarter.Q2, 6, 1100, 120, 95, 82, 11.0, None, None, 10.9),
        ),
    )
    assert "2025.3　10.0億|10.0%||10.0円" in text
    assert "2025.6　11.0億|10.9%||11.0円" in text


def test_build_kabutan_forecast_output_section_order_includes_quarterly_after_annual():
    pair = KabutanForecastPair(
        previous2_actual=None,
        previous_actual=KabutanForecastRow("2025.03", 2025, 3, "実績", 1000, 100, 90, 80),
        current_actual=None,
        current_forecast=KabutanForecastRow("2026.03", 2026, 3, "予想", 1200, 130, 120, 110),
        next_forecast=None,
    )
    text = build_kabutan_forecast_output(
        "base",
        pair,
        "html",
        None,
        (),
        None,
        (),
        (QuarterlyMetricRow(2025, Quarter.Q1, 3, 1000, 100, 90, 80, 10.0, None, None, 10.0),),
    )
    annual_pos = text.find("■株探 通期業績推移")
    quarterly_pos = text.find("■四半期トレンド")
    assert annual_pos != -1
    assert quarterly_pos != -1
    assert annual_pos < quarterly_pos


def test_build_kabutan_forecast_output_quarterly_trend_non_standard_month_label():
    text = build_kabutan_forecast_output(
        "base",
        None,
        "none",
        None,
        (),
        None,
        (),
        (
            QuarterlyMetricRow(2025, Quarter.Q1, 12, 1000, 100, 90, 80, 10.0, 20.0, 15.0, 10.0, 8.5),
            QuarterlyMetricRow(2026, Quarter.Q1, 12, 1100, 120, 100, 90, 12.0, None, None, 10.9, None),
        ),
    )
    assert "2025.12　10.0億|10.0%|8.5%|10.0円" in text
    assert "2026.12　11.0億|10.9%||12.0円" in text


def test_format_quarterly_detail_formatter_is_kept_for_future_switching():
    from app.presentation.display_formatter import _format_quarterly_metrics_detail

    lines = _format_quarterly_metrics_detail(
        QuarterlyMetricsSection(
            rows=[
                QuarterlyMetricRow(2025, Quarter.Q1, 3, 1000, 100, 90, 80, 10.0, 20.0, 15.0, 10.0),
            ],
        )
    )

    assert "■四半期業績推移" in lines
    assert "2025.3　10.0億|1.0億(+20.0%)|0.9億|0.8億|10.0円(+15.0%)|10.0%|" in lines
