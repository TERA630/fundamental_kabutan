from types import SimpleNamespace

from app.domain.builders.technical_summary import build_technical_summary_markdown
from app.domain.models.technical_summary import TechnicalSummaryLine, TechnicalSummaryTable
from app.domain.policies.technical_summary import (
    build_d1_detail,
    build_d3_detail,
    build_d_detail_headline,
    build_dev25_risk_label,
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
    assert build_technical_strategy_lines(
        "D3",
        detail_code="D3強",
        support_pullback_range="97〜98円",
        vwap_pullback_range="99〜100円",
        risk_reward="RR2.40",
    )[0] == (
        "前場深押し○：押し目待ちは 99〜100円 または 97〜98円。RR2.40が良好なら可。"
    )


def test_build_d_detail_headline_uses_detail_specific_main_judgement():
    assert build_d_detail_headline("D1", ma25_distance_atr=2.0) == (
        "D1a 戻り途中・25日線接近｜監視優先。D3化なら小さく可"
    )
    assert build_d_detail_headline("D1", ma25_distance_atr=2.01) == (
        "D1b 戻り途中・25日線遠い｜監視優先。深指値は原則不可"
    )
    assert build_d_detail_headline("D1", ma25_distance_atr=None) == (
        "D1 判定保留｜判定保留。新規不可"
    )
    assert build_d_detail_headline("D2") == (
        "D2 底打ち候補｜支持線反発待ち｜支持線反発候補。原則VWAP回復待ち"
    )
    assert build_d_detail_headline("D3", volume_vs_avg20_pct=80) == (
        "D3強｜VWAP維持・出来高伴う｜小さく可。D3内で最有力"
    )
    assert build_d_detail_headline("D3", volume_vs_avg20_pct=60) == (
        "D3｜VWAP維持・出来高やや不足｜小さく可。出来高確認"
    )
    assert build_d_detail_headline("D3", volume_vs_avg20_pct=59.9) == (
        "D3弱｜反転形あるも出来高不足｜監視寄り。出来高不足"
    )
    assert build_d_detail_headline("D3", volume_vs_avg20_pct=80, dev25_pct=-3.0).endswith(
        "｜25日線奪回接近"
    )


def test_build_d_strategy_lines_cover_detail_classifications():
    d1a = build_technical_strategy_lines(
        "D1",
        detail_code="D1a",
        support_entry_range="97〜97.75円",
        risk_reward="RR1.80",
    )
    assert d1a[0].startswith("前場深押し△：地合い良好なら 97〜97.75円")
    assert "D3化なら小さく可" in d1a[1]

    d1b = build_technical_strategy_lines(
        "D1",
        detail_code="D1b",
        nearest_support="97",
        risk_reward="RR2.10",
    )
    assert "RR2.0以上なら最小ロットのみ（RR2.10）" in d1b[0]

    d1_hold = build_technical_strategy_lines("D1", detail_code="D1")
    assert d1_hold[0] == "前場深押し×：ATR距離不明のため指値算出不可。"

    d2 = build_technical_strategy_lines(
        "D2",
        support_entry_range="97〜97.75円",
        vwap_recovery_range="100〜101円",
        risk_reward="RR1.60",
    )
    assert d2[1].startswith("前場VWAP回復△：")
    assert "D3化すれば○" in d2[1]

    d3_weak = build_technical_strategy_lines(
        "D3",
        detail_code="D3弱",
        nearest_support="97",
        risk_reward="RR2.20",
    )
    assert "RR2.0以上で最小ロット（RR2.20）" in d3_weak[0]


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
            vwap_maintained_15m=True,
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
    assert headline.comment == "支持線反発待ち。"
    assert headline.next_action == "まだ入らない。VWAP回復待ち。"


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
    assert headline.comment == "支持線反発待ち。"
    assert headline.next_action == "まだ入らない。VWAP回復待ち。"


def test_d3_requires_vwap_maintenance_but_not_volume():
    base = dict(
        dev25_pct=-12.0,
        latest=105.0,
        vwap=100.0,
        focus_theme=False,
        high_breakout_count=1,
        low_higher_count=2,
        day_close_position=0.65,
    )

    assert classify_technical_summary_rank(**base, vwap_maintained_15m=False) == "D1"
    assert (
        classify_technical_summary_rank(
            **base,
            vwap_maintained_15m=True,
            volume_vs_avg20_pct=40.0,
        )
        == "D3"
    )


def test_d1_and_d3_detail_labels_follow_atr_and_volume_boundaries():
    assert build_d1_detail(ma25_distance_atr=-2.0) == ("D1a", "戻り途中・25日線接近")
    assert build_d1_detail(ma25_distance_atr=-2.01) == ("D1b", "戻り途中・25日線遠い")
    assert build_d3_detail(volume_vs_avg20_pct=80.0) == ("D3強", "VWAP維持・出来高伴う")
    assert build_d3_detail(volume_vs_avg20_pct=60.0) == ("D3", "VWAP維持・出来高やや不足")
    assert build_d3_detail(volume_vs_avg20_pct=59.9) == ("D3弱", "反転形あるも出来高不足")


def test_d_rank_deviation_labels_do_not_change_classification():
    assert build_dev25_risk_label("D2", -16.0) == "深掘れ反発候補・リスク大"
    assert build_dev25_risk_label("D3", -16.0) == "急落リバ・戻り売り警戒"


def test_d2_excludes_clear_support_break_and_missing_direct_support():
    common = dict(
        dev25_pct=-6.0,
        vwap=100.0,
        focus_theme=False,
        day_open=99.0,
        day_high=100.0,
        day_close_position=0.6,
        atr14=2.0,
        volume_vs_avg20_pct=90.0,
        rsi14=40.0,
        low_higher_count=1,
    )
    assert (
        classify_technical_summary_rank(
            **common,
            latest=97.0,
            day_low=96.0,
            previous_low=98.0,
        )
        == "E"
    )
    assert (
        classify_technical_summary_rank(
            **common,
            latest=99.0,
            day_low=98.8,
            previous_low=95.0,
        )
        == "E"
    )


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

    assert assessment.collapse_risk_score == 0
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
