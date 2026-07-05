from app.domain.builders.hybrid_evaluation_output import build_hybrid_evaluation_text
from app.domain.models.fundamental_summary import FundamentalSummaryRow
from app.domain.models.technical_summary import TechnicalSummaryLine, TechnicalSummaryRow
from app.domain.policies.hybrid_classification import classify_hybrid_candidate
from app.domain.usecases.hybrid_evaluation import HybridEvaluationService


def test_hybrid_classification_treats_missing_resistance_as_f2_upside():
    result = classify_hybrid_candidate(
        fundamental_score=70,
        quality_score=45,
        latest=101,
        vwap=100,
        dev25_pct=1.5,
        day_close_position=0.65,
        volume_vs_avg20_pct=90,
        high_breakout_count=0,
        low_lower_count=0,
        previous_low_maintained=True,
        collapse_risk_score=0,
        resistance_upside_pct=None,
        volume_spike_bearish=False,
    )

    assert result is not None
    assert result.tag == "F2"
    assert "抵抗なし" in result.reasons


def test_hybrid_classification_prioritizes_m2_and_uses_150pct_bearish_volume():
    result = classify_hybrid_candidate(
        fundamental_score=80,
        quality_score=50,
        latest=108,
        vwap=100,
        dev25_pct=9.0,
        day_close_position=0.7,
        volume_vs_avg20_pct=150,
        high_breakout_count=1,
        low_lower_count=0,
        previous_low_maintained=True,
        collapse_risk_score=1,
        resistance_upside_pct=5.0,
        volume_spike_bearish=True,
    )

    assert result is not None
    assert result.tag == "M2"
    assert "出来高150%以上陰線" in result.reasons


def test_hybrid_evaluation_text_renders_single_stock_classification():
    fundamental_row = FundamentalSummaryRow(
        name="候補",
        code4="1234",
        total_score=72,
        quality_score=44,
        growth_score=None,
        valuation_score=None,
        operating_margin=None,
        operating_profit_cagr_3y=None,
        roic=None,
        cash_conversion=None,
        per=None,
        investment_rate=None,
    )
    technical_row = _technical_row(
        name="候補",
        code4="1234",
        dev25_pct=-4.0,
        vwap=100.0,
        vwap_diff_pct=2.0,
        high_breakout_count=1,
        low_lower_count=1,
        volume_vs_avg20_pct=85.0,
    )

    evaluation = HybridEvaluationService().build_evaluation(
        fundamental_row=fundamental_row,
        technical_row=technical_row,
    )
    text = build_hybrid_evaluation_text(evaluation)

    assert "■Hybrid評価" in text
    assert "分類：F1 高ファンダ深押し反転候補" in text
    assert "F：72 / Q：44" in text
    assert "Tech：" not in text
    assert "現在値：" not in text
    assert "25ME dev：" not in text
    assert "VWAP：" not in text
    assert "終端：" not in text
    assert "出来高：" not in text
    assert "崩れ：" not in text
    assert "抵抗余地：" not in text
    assert "理由：F72 / 高値更新1 / 安値切下げ1 / 出来高85%" in text


def _technical_row(
    *,
    name: str,
    code4: str,
    dev25_pct: float,
    vwap: float,
    vwap_diff_pct: float,
    high_breakout_count: int,
    low_lower_count: int,
    volume_vs_avg20_pct: float,
) -> TechnicalSummaryRow:
    return TechnicalSummaryRow(
        name=name,
        code4=code4,
        rank="D3",
        rank_label="底打ち初動",
        latest=102.0,
        day_change_price=1.0,
        day_change_pct=1.0,
        three_session_change_pct=0.0,
        day_high=104.0,
        day_low=98.0,
        day_close_position=0.67,
        day_range_atr=1.0,
        vwap=vwap,
        vwap_diff_pct=vwap_diff_pct,
        dev25_pct=dev25_pct,
        ma25_distance_atr=-1.0,
        volume_vs_avg20_pct=volume_vs_avg20_pct,
        previous_vwap_maintained=None,
        support_lines=(),
        resistance_lines=(TechnicalSummaryLine("20D-H", 110.0),),
        recent60_range_position=0.5,
        collapse_risk_score=1,
        high_breakout_count=high_breakout_count,
        low_higher_count=2,
        low_lower_count=low_lower_count,
        previous_low_maintained=True,
        volume_spike_bearish=False,
    )
