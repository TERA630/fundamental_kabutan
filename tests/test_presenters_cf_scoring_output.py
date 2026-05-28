import pytest

from app.domain.models.cf_scoring_result import CategoryScore, CfScoringResult, MetricScore, TotalScore
from app.domain.builders.fundamental_output import build_fundamental_output_sections
from app.domain.models.display_sections import SummarySection, ValuationTableSection
from app.presentation.display_formatter import format_sections
from app.presenters import build_cf_scoring_summary_text, build_fundamental_output


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
    assert "Quality: 45/60" in text
    assert "Growth: 20/25" in text
    assert "Valuation: 8/15" in text
    assert "FCF Yield: 2.50% -> B(4/10)" in text
    assert "ROIC: 18.20 -> B(9/15)" in text
    assert "ルール注記:" in text
    assert "成長投資免責によるランク引き上げ" in text


def test_build_fundamental_output_appends_scoring_when_present():
    out = build_fundamental_output(
        name="Test",
        code4="1234",
        master=None,
        price=1000.0,
        market_cap=1_000_000_000.0,
        cf_scoring_result=_sample_scoring(),
    )
    assert "■rankCF スコア" not in out
    assert "総合評価：　A (73/100点) バージョン: rankcf-v1" in out
    assert "投資分類： 標準的な強銘柄" in out
    assert "投資戦略：　トレンド・地合い次第で順張り。" in out
    assert "算出基準： 2026-05-27" in out
    assert "Quality: 45/60" in out
    assert out.find("業種：") < out.find("総合評価：") < out.find("■バリュエーション")
    assert out.find("■バリュエーション") < out.find("Quality: 45/60") < out.find("■株探 通期業績推移")


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
    assert "■バリュエーション" in formatted
    assert "年度|N/A" in formatted
    assert "PER|N/A" in formatted
    assert "配当利回り|N/A" in formatted


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
    assert "Quality: 0/60" in text
    assert "Growth: 0/25" in text
    assert "Valuation: 0/15" in text
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
