from types import SimpleNamespace

from app.domain.builders.technical_summary import build_technical_summary_markdown
from app.domain.models.technical_summary import TechnicalSummaryLine, TechnicalSummaryTable
from app.domain.policies.technical_summary import (
    build_technical_headline_summary,
    build_nearby_resistance_lines,
    build_nearby_support_lines,
    build_technical_position_assessment,
    build_technical_strategy_lines,
    classify_technical_summary_rank,
)
from app.domain.usecases.technical_summary import TechnicalSummaryService


def test_build_technical_strategy_lines_uses_rank_criteria_and_support_prices():
    assert build_technical_strategy_lines("A1", support_range="97〜98")[0] == (
        "前場深押し○：支持線付近 97〜98円で検討。約定後はVWAP回復・維持を確認。"
    )
    assert build_technical_strategy_lines("B1", nearest_support="98")[0] == (
        "前場深押し△：支持線付近 98円でのみ小さく検討。VWAP未回復なら撤退。"
    )
    assert build_technical_strategy_lines("D3") == ("N/A（判定基準未設定）",)


def test_classify_technical_summary_rank_uses_focus_theme_thresholds():
    assert classify_technical_summary_rank(dev25_pct=4.5, latest=105, vwap=100, focus_theme=True) == "A2"
    assert classify_technical_summary_rank(dev25_pct=7.5, latest=105, vwap=100, focus_theme=True) == "B1"
    assert classify_technical_summary_rank(dev25_pct=6.5, latest=105, vwap=100, focus_theme=False) == "A2"
    assert (
        classify_technical_summary_rank(
            dev25_pct=8.5,
            latest=95,
            vwap=100,
            focus_theme=False,
            recent60_range_position=0.85,
        )
        == "B1"
    )


def test_classify_technical_summary_rank_covers_c_and_e_cases():
    assert classify_technical_summary_rank(dev25_pct=3.0, latest=95, vwap=100, focus_theme=False) == "C1"
    assert classify_technical_summary_rank(dev25_pct=-3.0, latest=105, vwap=100, focus_theme=False) == "D1"
    assert classify_technical_summary_rank(dev25_pct=-3.0, latest=95, vwap=100, focus_theme=False) == "E"


def test_classify_technical_summary_rank_covers_bottoming_start():
    assert (
        classify_technical_summary_rank(
            dev25_pct=-3.0,
            latest=105,
            vwap=100,
            focus_theme=False,
            high_breakout_count=1,
            low_higher_count=2,
            day_close_position=0.65,
        )
        == "D3"
    )


def test_d2_bottoming_candidate_requires_support_rebound_and_vwap_proximity():
    rank = classify_technical_summary_rank(
        dev25_pct=-6.0,
        latest=99.0,
        vwap=100.0,
        focus_theme=False,
        day_open=99.6,
        day_high=100.0,
        day_low=97.4,
        day_close_position=0.62,
        atr14=2.0,
        volume_vs_avg20_pct=90.0,
        rsi14=40.0,
        low_higher_count=1,
        previous_low=98.0,
    )

    assert rank == "D2"


def test_d2_headline_uses_strong_comment_when_two_auxiliary_conditions_pass():
    headline = build_technical_headline_summary(
        dev25_pct=-6.0,
        latest=99.0,
        vwap=100.0,
        day_open=99.6,
        day_high=100.0,
        day_low=97.4,
        day_close_position=0.62,
        atr14=2.0,
        volume_vs_avg20_pct=90.0,
        rsi14=40.0,
        low_higher_count=1,
        previous_low=98.0,
    )

    assert headline.rank == "D2"
    assert headline.comment == "底打ち候補強。"
    assert headline.next_action == "VWAP回復待ち(補助指標2つ以上)。"


def test_d2_headline_uses_weak_comment_even_without_auxiliary_conditions():
    headline = build_technical_headline_summary(
        dev25_pct=-6.0,
        latest=99.0,
        vwap=100.0,
        day_open=98.2,
        day_high=100.0,
        day_low=98.0,
        day_close_position=0.5,
        atr14=2.0,
        volume_vs_avg20_pct=50.0,
        rsi14=55.0,
        low_higher_count=1,
        previous_low=98.0,
    )

    assert headline.rank == "D2"
    assert headline.comment == "底打ち候補。"
    assert headline.next_action == "買い急がず(補助指標1つ以下)。"


def test_d2_exclusion_falls_to_downtrend():
    assert (
        classify_technical_summary_rank(
            dev25_pct=-6.0,
            latest=97.8,
            vwap=100.0,
            focus_theme=False,
            day_open=99.0,
            day_high=100.0,
            day_low=97.6,
            day_close_position=0.6,
            atr14=2.0,
            volume_vs_avg20_pct=90.0,
            rsi14=40.0,
            low_higher_count=1,
            previous_low=98.0,
        )
        == "E"
    )


def test_build_nearby_support_and_resistance_lines_select_two_nearest():
    support = build_nearby_support_lines(
        latest=100,
        ma25=98,
        previous_low=94,
        recent20_low=97,
        ma75=90,
        recent60_low=80,
    )
    resistance = build_nearby_resistance_lines(
        latest=100,
        previous_high=103,
        recent20_high=110,
        recent60_high=105,
        ma25=98,
    )

    assert support == (TechnicalSummaryLine("25ME", 98), TechnicalSummaryLine("20D-L", 97))
    assert resistance == (TechnicalSummaryLine("PrevH", 103), TechnicalSummaryLine("60D-H", 105))


def test_position_assessment_scores_all_collapse_risk_conditions():
    assessment = build_technical_position_assessment(
        latest=90.0,
        vwap=92.0,
        ma25=95.0,
        atr14=5.0,
        day_open=91.0,
        day_high=93.0,
        day_low=89.0,
        day_close_position=0.3,
        volume_vs_avg20_pct=120.0,
        high_breakouts=(False, False, False),
        low_highers=(False, False, False),
        previous_low=85.0,
        recent20_low=80.0,
        ma75=70.0,
        recent60_low=60.0,
        headline_rank="E",
    )

    assert assessment.collapse_risk_score == 7
    assert assessment.collapse_risk_level == "高"
    assert assessment.hold_judgement == "×"
    assert assessment.bottoming_start_established is False


def test_position_assessment_requires_all_three_momentum_marks_to_fail():
    assessment = build_technical_position_assessment(
        latest=101.0,
        vwap=100.0,
        ma25=100.0,
        atr14=2.0,
        day_open=100.0,
        day_high=102.0,
        day_low=99.0,
        day_close_position=0.6,
        volume_vs_avg20_pct=90.0,
        high_breakouts=(False, False, True),
        low_highers=(False, False, True),
        previous_low=100.0,
        recent20_low=95.0,
        ma75=90.0,
        recent60_low=80.0,
        headline_rank="A1",
    )

    assert assessment.collapse_risk_score == 0
    assert assessment.collapse_risk_level == "低"
    assert assessment.hold_judgement == "◎"


def test_position_assessment_counts_volume_with_upper_price_stalling():
    assessment = build_technical_position_assessment(
        latest=101.0,
        vwap=100.0,
        ma25=100.0,
        atr14=2.0,
        day_open=100.8,
        day_high=102.8,
        day_low=99.0,
        day_close_position=0.5,
        volume_vs_avg20_pct=101.0,
        high_breakouts=(True, True, True),
        low_highers=(True, True, True),
        previous_low=100.0,
        recent20_low=95.0,
        ma75=90.0,
        recent60_low=80.0,
        headline_rank="A1",
    )

    assert assessment.collapse_risk_score == 1
    assert assessment.collapse_risk_level == "低"


def test_position_assessment_marks_d3_below_ma25_as_bottoming_start():
    assessment = build_technical_position_assessment(
        latest=99.0,
        vwap=98.0,
        ma25=100.0,
        atr14=2.0,
        day_open=98.0,
        day_high=100.0,
        day_low=97.0,
        day_close_position=0.7,
        volume_vs_avg20_pct=100.0,
        high_breakouts=(False, False, True),
        low_highers=(False, True, True),
        previous_low=98.0,
        recent20_low=95.0,
        ma75=90.0,
        recent60_low=80.0,
        headline_rank="D3",
    )

    assert assessment.bottoming_start_established is True
    assert assessment.hold_judgement == "△"


def test_technical_summary_service_builds_row_and_markdown():
    result = SimpleNamespace(
        name="AIテスト",
        code4="1234",
        snapshot=SimpleNamespace(
            price=SimpleNamespace(
                latest=105.0,
                high=108.0,
                low=100.0,
                day_change_price=2.0,
                day_change_pct=1.94,
                volume=1200.0,
                volume_avg20=1000.0,
            ),
            moving_average=SimpleNamespace(
                ma25=101.0,
                ma75=95.0,
                ma25_prev5=101.0,
                dev25_pct=3.96,
                ma25_distance_atr=0.8,
            ),
            range=SimpleNamespace(day_range_atr=1.1),
            previous_session=SimpleNamespace(prev_low=99.0, prev_high=109.0),
            breakline=SimpleNamespace(
                recent20_low=97.0,
                recent60_low=90.0,
                recent20_high=112.0,
                recent60_high=120.0,
                recent60_range_position=0.75,
            ),
        ),
        vwap_snapshot={"vwap": 102.0},
        previous_intraday_snapshot={"prev_am_vwap_maintained": True, "prev_pm_vwap_maintained": False},
        three_session_momentum=SimpleNamespace(change_pct=-2.5),
    )
    service = TechnicalSummaryService(lambda _name, _code4: result)

    table = service.build_summary_table([("AIテスト", "1234")])
    markdown = build_technical_summary_markdown(table)

    assert isinstance(table, TechnicalSummaryTable)
    assert table.rows[0].rank == "A1"
    assert table.rows[0].previous_vwap_maintained is False
    assert table.rows[0].headline_comment == "順張り可。過熱なし。"
    assert "## A1 位置良好" in markdown
    assert "## 冒頭短評" in markdown
    assert "A1 位置良好｜順張り可。過熱なし。" in markdown
    assert "25ME dev" in markdown
    assert "102円(+2.9%)" in markdown
    assert "AIテスト(1234)" in markdown
