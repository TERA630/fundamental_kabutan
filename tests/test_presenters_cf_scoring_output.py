from app.domain.models.cf_scoring_result import CategoryScore, CfScoringResult, MetricScore, TotalScore
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
    assert "■rankCF スコア" in text
    assert "合計: 73/100" in text
    assert "Quality: 45/60" in text
    assert "Growth: 20/25" in text
    assert "Valuation: 8/15" in text
    assert "FCF Yield: 2.50% -> B(4/10)" in text
    assert "ROIC: 18.20 -> B(9/15)" in text
    assert "ルール注記:" in text
    assert "growth_exemption: fcf_ratio promoted to A(7)" in text


def test_build_fundamental_output_appends_scoring_when_present():
    out = build_fundamental_output(
        name="Test",
        code4="1234",
        master=None,
        price=1000.0,
        market_cap=1_000_000_000.0,
        cf_scoring_result=_sample_scoring(),
    )
    assert "■rankCF スコア" in out
    assert "合計: 73/100" in out


def test_build_fundamental_output_without_scoring_keeps_previous_behavior():
    out = build_fundamental_output(
        name="Test",
        code4="1234",
        master=None,
        price=1000.0,
        market_cap=1_000_000_000.0,
    )
    assert "■rankCF スコア" not in out
