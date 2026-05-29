import pytest

from app.domain.models.cf_scoring_result import CategoryScore, CfScoringResult, MetricScore, TotalScore
from app.domain.builders.fundamental_output import build_fundamental_output_sections
from app.domain.models.display_sections import (
    DisplaySections,
    OpeningSummarySection,
    RuleNotesSection,
    ScoreCategorySection,
    ScoreSummarySection,
    SummarySection,
    ValuationTableSection,
)
from app.presentation.display_formatter import format_sections
from app.presenters import build_cf_scoring_sections, build_cf_scoring_summary_text, build_fundamental_output


def _sample_scoring() -> CfScoringResult:
    return CfScoringResult(
        version="rankcf-v1",
        as_of="2026-05-27",
        quality=CategoryScore(
            category="quality",
            subtotal=45,
            max_points=60,
            metrics=(
                MetricScore("roic", "quality", 18.2, "B", 9, 15),
                MetricScore("fcf_ratio", "quality", -10.0, "A", 7, 10, ("growth_exemption: fcf_ratio promoted to A(7)",)),
            ),
        ),
        growth=CategoryScore(
            category="growth",
            subtotal=20,
            max_points=25,
            metrics=(MetricScore("sales_cagr_3y", "growth", 16.0, "A", 8, 10),),
        ),
        valuation=CategoryScore(
            category="valuation",
            subtotal=8,
            max_points=15,
            metrics=(
                MetricScore("fcf_yield", "valuation", 2.5, "B", 4, 10),
                MetricScore("per", "valuation", 40.0, "C", 2, 5, ("high_growth_bonus: +1 point",)),
            ),
        ),
        total=TotalScore(
            total_points=73,
            max_points=100,
            judgement="A",
            investment_category="標準的な強銘柄",
            investment_strategy="トレンド・地合い次第で順張り。",
            priority_hint=None,
        ),
    )


def test_build_cf_scoring_summary_text_renders_total_breakdown_and_notes():
    text = build_cf_scoring_summary_text(_sample_scoring())
    assert "■rankCF スコア" not in text
    assert "総合評価" not in text
    assert "投資分類" not in text
    assert "投資戦略" not in text
    assert "合計: 73/100" not in text
    assert "[Quality] 45/60" in text
    assert "[Growth] 20/25" in text
    assert "[Valuation] 8/15" in text
    assert "FCF Yield    B    4/10 2.50%" in text
    assert "ROIC               B    9/15 18.20" in text
    assert "ルール注記:" in text
    assert "成長投資免責によるランク引き上げ" in text


def test_build_cf_scoring_sections_builds_score_display_dtos():
    sections = build_cf_scoring_sections(_sample_scoring(), include_summary=True)

    assert isinstance(sections[0], ScoreSummarySection)
    assert isinstance(sections[1], ScoreCategorySection)
    assert isinstance(sections[2], ScoreCategorySection)
    assert isinstance(sections[3], ScoreCategorySection)
    assert isinstance(sections[4], RuleNotesSection)
    assert sections[1].title == "Quality"
    assert sections[2].title == "Growth"
    assert sections[3].title == "Valuation"


def test_format_opening_summary_section():
    formatted = format_sections(
        DisplaySections(
            sections=[
                OpeningSummarySection(
                    company_name="ハーモニック・ドライブ・システム",
                    code4="6324",
                    price=7690.0,
                    market_cap=727_900_000_000.0,
                    market_cap_class="中型主役",
                    judgement="B",
                    total_points=49,
                    max_points=100,
                    growth_phase="利益改善型",
                    per_level="超高PER",
                    roic_level="低ROIC",
                    investment_strategy="順張り対象外・逆張り限定",
                )
            ]
        )
    )

    assert formatted.splitlines() == [
        "【ハーモニック・ドライブ・システム (6324)】",
        "株価 7,690円　時価総額 7,279億円（中型主役）",
        "",
        "総合評価 B（49/100）",
        "利益改善型 / 超高PER / 低ROIC",
    ]


def test_format_opening_summary_section_fallbacks():
    formatted = format_sections(
        DisplaySections(
            sections=[
                OpeningSummarySection(
                    company_name="Test",
                    code4="1234",
                    price=None,
                    market_cap=None,
                    market_cap_class=None,
                    judgement=None,
                    total_points=None,
                    max_points=None,
                    growth_phase=None,
                    per_level=None,
                    roic_level=None,
                    investment_strategy=None,
                )
            ]
        )
    )

    assert "株価 N/A　時価総額 N/A" in formatted
    assert "総合評価 N/A" in formatted
    assert "N/A / N/A / N/A" in formatted
    assert "投資戦略" not in formatted


def test_build_fundamental_output_uses_opening_summary_when_scoring_present():
    out = build_fundamental_output(
        name="Test",
        code4="1234",
        master=None,
        price=1000.0,
        market_cap=1_000_000_000.0,
        cf_scoring_result=_sample_scoring(),
        growth_phase="安定成長",
        per_level="適正PER",
        roic_level="高ROIC",
    )
    assert "■rankCF スコア" not in out
    assert "【Test (1234)】" in out
    assert "株価 1,000円　時価総額 10億円（小型）" in out
    assert "総合評価 A（73/100）" in out
    assert "安定成長 / 適正PER / 高ROIC" in out
    assert "トレンド・地合い次第で順張り。" not in out
    assert "逆張り" not in out
    assert "投資戦略" not in out
    assert "投資分類：" not in out
    assert "算出基準：" not in out
    assert "総合評価：" not in out
    assert "[Quality] 45/60" in out
    assert out.find("【Test (1234)】") < out.find("総合評価 A（73/100）") < out.find("■株価評価・資本効率")
    assert out.find("■株価評価・資本効率") < out.find("[Quality] 45/60") < out.find("■株探 通期業績推移")


def test_build_fundamental_output_without_scoring_keeps_previous_behavior():
    out = build_fundamental_output(
        name="Test",
        code4="1234",
        master=None,
        price=1000.0,
        market_cap=1_000_000_000.0,
    )
    assert "■rankCF スコア" not in out


def test_build_fundamental_output_sections_and_formatter_produces_valuation_table():
    sections = build_fundamental_output_sections(
        name="Test",
        code4="1234",
        master=None,
        price=1000.0,
        market_cap=1_000_000_000.0,
    )

    assert len(sections.sections) == 2
    assert isinstance(sections.sections[0], SummarySection)
    assert isinstance(sections.sections[1], ValuationTableSection)
    assert sections.sections[0].company_name == "Test"
    assert sections.sections[1].year_labels == []
    assert sections.sections[1].per_values == ["N/A"]
    assert sections.sections[1].dividend_values == ["N/A"]

    formatted = format_sections(sections)
    assert "■株価評価・資本効率" in formatted
    assert "年度|N/A" in formatted
    assert "PER|N/A" in formatted
    assert "配当利回り|N/A" in formatted


def test_build_fundamental_output_integrates_capital_efficiency_into_valuation_block():
    from app.domain.models.financial_snapshot import FinancialMetricInputRow
    from app.domain.models.kabutan_cashflow import KabutanCashflowRow
    from app.domain.models.kabutan_forecast import KabutanForecastPair, KabutanForecastRow

    pair = KabutanForecastPair(
        previous2_actual=None,
        previous_actual=KabutanForecastRow("2025.03", 2025, 3, "実績", 1000, 100, 90, 80, 100.0, 20.0),
        current_actual=None,
        current_forecast=None,
        next_forecast=None,
    )

    out = build_fundamental_output(
        name="Test",
        code4="1234",
        master=None,
        price=2000.0,
        market_cap=10_000_000_000.0,
        kabutan_forecast_pair=pair,
        kabutan_cashflow_rows=(KabutanCashflowRow("2025.03", 2025, 3, 200, 300, -100, 0, 500),),
        financial_metric_rows=(
            FinancialMetricInputRow(
                year=2025,
                net_income=80,
                equity=400,
                operating_profit=100,
                interest_bearing_debt=100,
                bps=1000.0,
                price=2000.0,
            ),
        ),
    )

    valuation_pos = out.find("■株価評価・資本効率")
    forecast_pos = out.find("■株探 通期業績推移")
    assert valuation_pos != -1
    assert valuation_pos < forecast_pos
    assert "PER|20.0倍" in out
    assert "PBR|2.00倍" in out
    assert "ROE|20.00%" in out
    assert "ROIC|14.00%" in out
    assert "配当利回り|1.00%" in out
    assert "FCF Yield|2.00%" in out
    assert "■財務ブロック" not in out


def test_format_sections_logs_missing_valuation_values(caplog):
    sections = build_fundamental_output_sections(
        name="Test",
        code4="1234",
        master=None,
        price=1000.0,
        market_cap=1_000_000_000.0,
    )

    caplog.set_level("INFO")
    format_sections(sections)

    assert "取得不可: PER (値欠損)" in caplog.text
    assert "取得不可: 配当利回り (値欠損)" in caplog.text


def test_build_cf_scoring_summary_text_omits_na_metrics_and_logs(caplog):
    scoring = CfScoringResult(
        version="rankcf-v1",
        as_of="2026-05-27",
        quality=CategoryScore(
            category="quality",
            subtotal=0,
            max_points=60,
            metrics=(
                MetricScore("roic", "quality", None, "N/A", 0, 15),
                MetricScore("fcf_ratio", "quality", None, "N/A", 0, 10),
            ),
        ),
        growth=CategoryScore(
            category="growth",
            subtotal=0,
            max_points=25,
            metrics=(MetricScore("sales_cagr_3y", "growth", None, "N/A", 0, 10),),
        ),
        valuation=CategoryScore(
            category="valuation",
            subtotal=0,
            max_points=15,
            metrics=(MetricScore("fcf_yield", "valuation", None, "N/A", 0, 10),),
        ),
        total=TotalScore(
            total_points=0,
            max_points=100,
            judgement="C",
            investment_category="対象外",
            investment_strategy="基本ノータッチ",
            priority_hint=None,
        ),
    )
    caplog.set_level("DEBUG")
    text = build_cf_scoring_summary_text(scoring)
    assert "[Quality] 0/60" in text
    assert "[Growth] 0/25" in text
    assert "[Valuation] 0/15" in text
    assert "投資分類" not in text
    assert "投資戦略" not in text
    assert "ROIC:" not in text
    assert "FCF Ratio" not in text
    assert "取得不可: ROIC (値欠損)" in caplog.text
    assert "取得不可: FCF Yield (値欠損)" in caplog.text


def test_build_cf_scoring_summary_text_rule_note_fallback_for_unknown_key():
    scoring = CfScoringResult(
        version="rankcf-v1",
        as_of="2026-05-27",
        quality=CategoryScore(
            category="quality",
            subtotal=10,
            max_points=60,
            metrics=(MetricScore("roic", "quality", 10.0, "C", 6, 15, ("unknown_rule: detail",)),),
        ),
        growth=CategoryScore(category="growth", subtotal=0, max_points=25, metrics=()),
        valuation=CategoryScore(category="valuation", subtotal=0, max_points=15, metrics=()),
        total=TotalScore(
            total_points=10,
            max_points=100,
            judgement="C",
            investment_category="対象外",
            investment_strategy="基本ノータッチ",
            priority_hint=None,
        ),
    )
    text = build_cf_scoring_summary_text(scoring)
    assert "未定義ルール: unknown_rule: detail" in text


@pytest.mark.parametrize(
    ("raw_note", "expected"),
    [
        ("high_growth_bonus: +1 point", "高グロース株加点"),
        ("growth_floor: fcf_yield raised to C(2)", "高成長考慮による下限補正"),
        ("growth_exemption: fcf_ratio promoted to A(7)", "成長投資免責によるランク引き上げ"),
        ("quality_filter: ocf/op < 0.7 capped to C(5)", "品質フィルター適用（OCF/営業利益）"),
        ("invalid_per: per <= 0", "PER算出値不正"),
        ("invalid_sign: net_income <= 0", "純利益符号不正"),
        ("invalid_sign: ocf <= 0", "営業CF符号不正"),
        ("invalid_sign: ocf == 0", "営業CFゼロ"),
        ("invalid_sign: ocf < 0", "営業CFマイナス"),
    ],
)
def test_build_cf_scoring_summary_text_localizes_rule_notes(raw_note, expected):
    scoring = CfScoringResult(
        version="rankcf-v1",
        as_of="2026-05-27",
        quality=CategoryScore(
            category="quality",
            subtotal=10,
            max_points=60,
            metrics=(MetricScore("roic", "quality", 10.0, "C", 6, 15, (raw_note,)),),
        ),
        growth=CategoryScore(category="growth", subtotal=0, max_points=25, metrics=()),
        valuation=CategoryScore(category="valuation", subtotal=0, max_points=15, metrics=()),
        total=TotalScore(10, 100, "C", "対象外", "基本ノータッチ", None),
    )
    text = build_cf_scoring_summary_text(scoring)
    assert expected in text
