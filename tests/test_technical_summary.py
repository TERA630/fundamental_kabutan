from datetime import datetime
from types import SimpleNamespace

import pandas as pd

from app.domain.builders.technical_summary import build_technical_summary_markdown
from app.domain.models.technical_summary import TechnicalSummaryLine, TechnicalSummaryRow, TechnicalSummaryTable
from app.domain.models.us_market_summary import UsMarketSummaryRow, UsMarketSummaryTable
from app.domain.policies.technical_summary import (
    build_collapse_score_brief,
    build_d1_detail,
    build_d2_detail,
    build_d3_detail,
    build_d_detail_headline,
    build_dev25_risk_label,
    build_ma5_slope_short_comment,
    build_technical_headline_summary,
    build_technical_short_comment,
    build_nearby_resistance_lines,
    build_nearby_support_lines,
    build_technical_position_assessment,
    build_technical_strategy_lines,
    build_volume_comment,
    classify_technical_summary_rank,
)
from app.presentation.web_technical_summary import build_technical_summary_html
from app.domain.usecases.technical_summary import TechnicalSummaryService
from app.domain.usecases.us_market_summary import UsMarketSummaryService


def _daily_history(rows: int = 70) -> pd.DataFrame:
    index = pd.date_range("2026-01-01", periods=rows, freq="B")
    close = pd.Series(range(100, 100 + rows), index=index, dtype=float)
    return pd.DataFrame(
        {
            "Open": close - 1,
            "High": close + 2,
            "Low": close - 3,
            "Close": close,
            "Volume": [1000 + i for i in range(rows)],
        },
        index=index,
    )


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
    assert build_d_detail_headline("D2", d2_detail_code="D2弱") == (
        "D2弱 底打ち候補・弱｜支持線根拠弱い｜支持線根拠が弱い。VWAP回復まで監視"
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


def test_classify_technical_summary_rank_uses_new_ma25_deviation_bands():
    assert classify_technical_summary_rank(dev25_pct=12.0, latest=112, vwap=100) == "B2"
    assert classify_technical_summary_rank(dev25_pct=10.0, latest=110, vwap=100) == "B1"
    assert classify_technical_summary_rank(dev25_pct=8.5, latest=108.5, vwap=100) == "A2"
    assert classify_technical_summary_rank(dev25_pct=6.5, latest=106.5, vwap=100) == "A1"
    assert classify_technical_summary_rank(dev25_pct=4.5, latest=104.5, vwap=100) == "A1弱"
    assert classify_technical_summary_rank(dev25_pct=3.5, latest=103.5, vwap=100) == "C1"
    assert (
        classify_technical_summary_rank(
            dev25_pct=8.5,
            latest=108.5,
            vwap=100,
            recent60_range_position=0.85,
        )
        == "B1"
    )
    assert (
        classify_technical_summary_rank(
            dev25_pct=10.0,
            latest=110.0,
            vwap=100.0,
            ma25_distance_atr=3.01,
        )
        == "B2"
    )


def test_a2_label_describes_mild_overheat():
    headline = build_technical_headline_summary(
        dev25_pct=8.5,
        latest=108.5,
        vwap=100.0,
    )

    assert headline.rank == "A2"
    assert headline.rank_label == "やや過熱"


def test_light_above_ma25_collapse_conditions_keep_base_rank_with_labels():
    assert (
        classify_technical_summary_rank(
            dev25_pct=6.0,
            latest=106.0,
            vwap=107.0,
        )
        == "A1"
    )

    headline = build_technical_headline_summary(
        dev25_pct=6.0,
        latest=106.0,
        vwap=107.0,
    )

    assert headline.rank == "A1"
    assert headline.collapse_state_label == "要確認"


def test_two_point_above_ma25_collapse_conditions_keep_base_rank_as_check_needed():
    headline = build_technical_headline_summary(
        dev25_pct=6.0,
        latest=106.0,
        vwap=107.0,
        high_breakouts=(False, False, False),
        low_highers=(True, True, True),
        high_breakout_count=0,
        low_higher_count=3,
    )

    assert headline.rank == "A1"
    assert headline.collapse_state_label == "要確認"


def test_three_point_above_ma25_collapse_conditions_keep_base_rank():
    headline = build_technical_headline_summary(
        dev25_pct=6.0,
        latest=106.0,
        vwap=107.0,
        high_breakouts=(False, False, False),
        low_highers=(False, False, False),
        high_breakout_count=0,
        low_higher_count=0,
    )

    assert headline.rank == "A1"
    assert headline.collapse_state_label == "要確認"


def test_mid_score_with_bad_price_structure_falls_to_c2():
    headline = build_technical_headline_summary(
        dev25_pct=6.0,
        latest=106.0,
        vwap=105.0,
        ma25=100.0,
        ma25_prev5=100.0,
        atr14=2.0,
        low_highers=(False, False, False),
        high_breakouts=(False, False, False),
        low_higher_count=0,
        high_breakout_count=0,
    )

    assert headline.rank == "C2"
    assert headline.c2_fall_reason == "崩れスコア中リスク＋価格構造悪化"


def test_high_score_falls_to_c2_even_without_immediate_trigger():
    headline = build_technical_headline_summary(
        dev25_pct=6.0,
        latest=106.0,
        vwap=105.0,
        ma25=100.0,
        ma25_prev5=100.0,
        ma5_slope=1.0,
        ma5_slope_prev=2.0,
        ma5_slope_3d_ago=3.0,
        atr14=2.0,
        low_highers=(False, False, False),
        high_breakouts=(False, False, False),
        low_higher_count=0,
        high_breakout_count=0,
    )

    assert headline.rank == "C2"
    assert headline.c2_fall_reason == "崩れスコア高リスク"


def test_ma5_score_two_points_only_keeps_base_rank():
    headline = build_technical_headline_summary(
        dev25_pct=6.0,
        latest=106.0,
        vwap=105.0,
        ma5_slope=0.0,
    )

    assert headline.rank == "A1"
    assert headline.collapse_state_label == "要確認"


def test_ma5_score_with_price_structure_falls_to_c2():
    assert (
        classify_technical_summary_rank(
            dev25_pct=6.0,
            latest=106.0,
            vwap=107.0,
            ma5_slope=0.0,
        )
        == "C2"
    )


def test_strong_collapse_condition_falls_to_c2_even_with_two_points():
    headline = build_technical_headline_summary(
        dev25_pct=6.0,
        latest=106.0,
        vwap=107.0,
        atr14=2.0,
        day_close_position=0.3,
    )

    assert headline.rank == "C2"
    assert headline.c2_fall_reason == "VWAP明確割れ＋終端位置低下"


def test_c2_short_comment_shows_fall_reason():
    comment = build_technical_short_comment(
        rank="C2",
        collapse_state_label="崩れ警戒",
        c2_fall_reason="VWAP明確割れ＋終端位置低下",
    )

    assert "C2陥落トリガー：VWAP明確割れ＋終端位置低下" in comment
    assert "C2 崩れ警戒 陥落トリガー" not in comment


def test_b_ranks_keep_rank_even_when_collapse_condition_is_strong():
    b2 = build_technical_headline_summary(
        dev25_pct=12.0,
        latest=112.0,
        vwap=113.0,
        atr14=2.0,
        day_close_position=0.3,
    )
    b1 = build_technical_headline_summary(
        dev25_pct=10.0,
        latest=110.0,
        vwap=111.0,
        atr14=2.0,
        day_close_position=0.3,
    )

    assert b2.rank == "B2"
    assert b2.collapse_state_label == "崩れ警戒"
    assert b1.rank == "B1"
    assert b1.collapse_state_label == "崩れ警戒"


def test_upper_price_stalling_uses_45_percent_wick_boundary():
    below_boundary = build_technical_headline_summary(
        dev25_pct=6.0,
        latest=112.0,
        vwap=100.0,
        day_open=110.0,
        day_high=120.0,
        day_low=100.0,
        day_close_position=0.3,
        volume_vs_avg20_pct=120.0,
    )
    at_boundary = build_technical_headline_summary(
        dev25_pct=6.0,
        latest=111.0,
        vwap=100.0,
        day_open=110.0,
        day_high=120.0,
        day_low=100.0,
        day_close_position=0.3,
        volume_vs_avg20_pct=120.0,
    )

    assert below_boundary.rank == "A1"
    assert below_boundary.collapse_state_label == "要確認"
    assert at_boundary.rank == "C2"
    assert at_boundary.collapse_state_label == "崩れ警戒"


def test_below_ma25_headline_omits_ranking_collapse_label():
    d_headline = build_technical_headline_summary(
        dev25_pct=-3.0,
        latest=105.0,
        vwap=100.0,
    )
    e_headline = build_technical_headline_summary(
        dev25_pct=-3.0,
        latest=95.0,
        vwap=100.0,
    )

    assert d_headline.rank == "D1"
    assert d_headline.collapse_state_label is None
    assert e_headline.rank == "E"
    assert e_headline.collapse_state_label is None


def test_volume_comment_parts_follow_boundaries():
    assert build_volume_comment(59.9) == "出来高薄い"
    assert build_volume_comment(60.0) == "出来高やや薄い"
    assert build_volume_comment(80.0) == "出来高通常"
    assert build_volume_comment(120.0) == "出来高伴う"
    assert build_volume_comment(180.0) == "出来高急増"
    assert build_volume_comment(None) == "出来高N/A"


def test_collapse_score_brief_follows_practical_score_bands():
    assert build_collapse_score_brief(0).text == "候補｜買い条件は別確認"
    assert build_collapse_score_brief(4).text == "候補｜買い条件は別確認"
    assert build_collapse_score_brief(5).text == "条件付き候補｜後場VWAP上維持・終端60%以上を確認"
    assert build_collapse_score_brief(6).text == "条件付き候補｜後場VWAP上維持・終端60%以上を確認"
    assert build_collapse_score_brief(7).text == "原則回避｜新規買い回避。前場深押し指値は避ける"
    assert build_collapse_score_brief(8).text == "かなり回避｜例外条件が揃う時だけ短期リバ検討"
    assert build_collapse_score_brief(9).text == "ほぼ触らない｜構造回復まで見送り"
    assert build_collapse_score_brief(11).text == "ほぼ触らない｜構造回復まで見送り"
    assert build_collapse_score_brief(None).text == "候補｜買い条件は別確認"


def test_ma5_slope_short_comment_follows_score_details():
    assert build_ma5_slope_short_comment(ma5_slope=1.0) == "5日線良好"
    assert (
        build_ma5_slope_short_comment(
            ma5_slope=-0.1,
            ma5_slope_prev=-0.2,
            ma5_slope_3d_ago=-0.3,
        )
        == "5日線下向き"
    )
    assert (
        build_ma5_slope_short_comment(
            ma5_slope=0.1,
            ma5_slope_prev=0.3,
            ma5_slope_3d_ago=0.2,
        )
        == "5日線鈍化・5日線失速"
    )
    assert (
        build_ma5_slope_short_comment(
            ma5_slope=-0.3,
            ma5_slope_prev=-0.1,
            ma5_slope_3d_ago=0.0,
        )
        == "5日線悪化"
    )


def test_classify_technical_summary_rank_covers_c_and_e_cases():
    assert classify_technical_summary_rank(dev25_pct=3.0, latest=103, vwap=100) == "C1"
    assert classify_technical_summary_rank(dev25_pct=-3.0, latest=105, vwap=100) == "D1"
    assert classify_technical_summary_rank(dev25_pct=-3.0, latest=95, vwap=100) == "E"


def test_classify_technical_summary_rank_covers_bottoming_start():
    assert (
        classify_technical_summary_rank(
            dev25_pct=-3.0,
            latest=105,
            vwap=100,
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


def test_d3_does_not_require_high_breakout_and_promotes_strong_detail():
    assert (
        classify_technical_summary_rank(
            dev25_pct=-12.0,
            latest=105.0,
            vwap=100.0,
            high_breakout_count=0,
            low_higher_count=2,
            day_close_position=0.65,
            vwap_maintained_15m=True,
        )
        == "D3"
    )
    assert build_d3_detail(
        volume_vs_avg20_pct=40.0,
        high_breakout_count=1,
        day_close_position=0.65,
    ) == ("D3強", "VWAP維持・高値更新")
    assert build_d3_detail(
        volume_vs_avg20_pct=40.0,
        high_breakout_count=0,
        day_close_position=0.70,
    ) == ("D3強", "VWAP維持・終端強い")


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


def test_d2_requires_point_one_atr_rebound_above_support():
    common = dict(
        dev25_pct=-6.0,
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
    assert classify_technical_summary_rank(**common, latest=98.19) == "E"
    assert classify_technical_summary_rank(**common, latest=98.20) == "D2"


def test_d2_weak_detail_for_standalone_previous_low_lower_lows_and_moderate_bearish():
    base = dict(
        latest=99.0,
        vwap=100.0,
        day_open=99.6,
        day_high=100.0,
        day_low=97.4,
        day_close_position=0.62,
        atr14=2.0,
        rsi14=40.0,
        previous_low=98.0,
    )
    assert build_d2_detail(
        **base,
        volume_vs_avg20_pct=90.0,
        recent20_low=None,
        ma75=None,
        recent60_low=None,
        low_highers=(True, True, True),
    ) == ("D2弱", "底打ち候補・弱")
    assert build_d2_detail(
        **base,
        volume_vs_avg20_pct=90.0,
        recent20_low=98.2,
        ma75=None,
        recent60_low=None,
        low_highers=(False, False, True),
    ) == ("D2弱", "底打ち候補・弱")
    assert build_d2_detail(
        **base,
        volume_vs_avg20_pct=120.0,
        recent20_low=98.2,
        ma75=None,
        recent60_low=None,
        low_highers=(True, True, True),
    ) == ("D2弱", "底打ち候補・弱")


def test_d2_big_bearish_volume_above_150_falls_to_downtrend():
    assert (
        classify_technical_summary_rank(
            dev25_pct=-6.0,
            latest=98.0,
            vwap=100.0,
            day_open=99.8,
            day_high=100.0,
            day_low=97.4,
            day_close_position=0.42,
            atr14=2.0,
            volume_vs_avg20_pct=151.0,
            rsi14=40.0,
            low_higher_count=1,
            previous_low=97.8,
            recent20_low=97.9,
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
        ma5=91.0,
        ma5_prev1=92.0,
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

    assert assessment.collapse_risk_score == 8
    assert assessment.collapse_risk_level == "高"
    assert assessment.hold_judgement == "×"
    assert assessment.bottoming_start_established is False
    signals = {signal.signal_id: signal for signal in assessment.collapse_risk_signals}
    assert "below_ma25" not in signals
    assert signals["vwap_clear_break"].matched is True
    assert signals["ma5_down"].points == 2


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


def test_position_assessment_scores_non_positive_ma5_slope_as_collapse_risk():
    assessment = build_technical_position_assessment(
        latest=101.0,
        vwap=100.0,
        ma25=100.0,
        ma5=100.8,
        ma5_prev1=101.0,
        ma25_prev5=99.0,
        atr14=2.0,
        day_open=100.0,
        day_high=102.0,
        day_low=99.0,
        day_close_position=0.6,
        volume_vs_avg20_pct=90.0,
        high_breakouts=(True, True, True),
        low_highers=(True, True, True),
        previous_low=100.0,
        recent20_low=95.0,
        ma75=90.0,
        recent60_low=80.0,
        headline_rank="A1",
    )

    assert assessment.collapse_risk_score == 2
    assert assessment.collapse_risk_label == "崩れ軽微"


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
                ma25=100.0,
                ma75=95.0,
                ma25_prev5=99.0,
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
    assert table.rows[0].rank == "A1弱"
    assert table.rows[0].previous_vwap_maintained is False
    assert table.rows[0].collapse_risk_score == 0
    assert table.rows[0].headline_comment == "良好だが、短期逆行も多い。"
    assert "## A1弱 押し目候補" in markdown
    assert "## 冒頭短評" not in markdown
    assert "A1弱 押し目候補｜良好だが、短期逆行も多い。" not in markdown
    assert "崩れスコア" in markdown
    assert "前日VWAP維持" not in markdown
    assert "| AIテスト(1234) | 105円(+1.9%) | -2.5% | 100-108円(終端:62%:値幅N/A) | 102円(+2.9%) | +5.0%(N/A) | 120% | 0 |" in markdown
    assert "25ME dev" in markdown
    assert "102円(+2.9%)" in markdown
    assert "AIテスト(1234)" in markdown


def test_technical_summary_service_sorts_above_ma25_ranks_by_collapse_score():
    rows_by_code = {
        "1111": _summary_row(name="Score3", code4="1111", rank="A1", collapse_risk_score=3),
        "2222": _summary_row(name="Score1A", code4="2222", rank="A1", collapse_risk_score=1),
        "3333": _summary_row(name="Score1B", code4="3333", rank="A1", collapse_risk_score=1),
        "4444": _summary_row(name="C2Score2", code4="4444", rank="C2", collapse_risk_score=2),
        "5555": _summary_row(name="C2Score0", code4="5555", rank="C2", collapse_risk_score=0),
    }

    class RowSortingService(TechnicalSummaryService):
        def build_summary_row(self, result):
            return result

    service = RowSortingService(lambda _name, code4: rows_by_code[code4])
    table = service.build_summary_table(
        [
            ("Score3", "1111"),
            ("Score1A", "2222"),
            ("Score1B", "3333"),
            ("C2Score2", "4444"),
            ("C2Score0", "5555"),
        ]
    )

    assert [row.code4 for row in table.rows if row.rank == "A1"] == ["2222", "3333", "1111"]
    assert [row.code4 for row in table.rows if row.rank == "C2"] == ["5555", "4444"]


def test_us_market_summary_service_builds_rows_and_skips_failures():
    service = UsMarketSummaryService(
        lambda ticker: pd.DataFrame() if ticker == "^SOX" else _daily_history(),
        clock=lambda: datetime(2026, 6, 17, 9, 0),
    )

    table = service.build_summary_table()

    assert table.as_of == datetime(2026, 6, 17, 9, 0)
    assert table.rows[0].name == "NASDAQ総合"
    assert table.rows[0].ticker == "^IXIC"
    assert table.rows[0].latest == 169.0
    assert table.rows[0].dev5_pct is not None
    assert table.skipped[0].name == "SOX指数"


def test_technical_summary_markdown_renders_us_market_section():
    table = TechnicalSummaryTable(
        rows=(),
        us_market=UsMarketSummaryTable(
            as_of=datetime(2026, 6, 17, 9, 0),
            rows=(
                UsMarketSummaryRow(
                    name="NASDAQ総合",
                    ticker="^IXIC",
                    latest=100.0,
                    day_change_pct=1.2,
                    dev5_pct=2.3,
                    dev25_pct=4.5,
                    rsi14=55.6,
                ),
            ),
        ),
    )

    markdown = build_technical_summary_markdown(table)

    assert "## US Market 2026-06-17 09:00" in markdown
    assert "| NASDAQ総合 | 100.00 | +1.2% | +2.3% | +4.5% | 55.60 |" in markdown


def test_technical_summary_html_does_not_render_headline_table():
    table = TechnicalSummaryTable(
        rows=(
            TechnicalSummaryRow(
                name="AIテスト",
                code4="1234",
                rank="A1",
                rank_label="位置良好",
                latest=105.0,
                day_change_price=2.0,
                day_change_pct=1.94,
                three_session_change_pct=-2.5,
                day_high=108.0,
                day_low=100.0,
                day_close_position=0.5,
                day_range_atr=1.1,
                vwap=102.0,
                vwap_diff_pct=2.94,
                dev25_pct=3.96,
                ma25_distance_atr=0.8,
                volume_vs_avg20_pct=120.0,
                previous_vwap_maintained=False,
                support_lines=(),
                resistance_lines=(),
                recent60_range_position=0.75,
                collapse_risk_score=2,
                headline_comment="順張り可。過熱なし。",
                next_action="深押し、VWAP回復、後場VWAP維持は可。追加買いは条件付き可。",
            ),
        )
    )

    html = build_technical_summary_html(table)

    assert "冒頭短評" not in html
    assert "technical-summary-headline-table" not in html
    assert "A1 位置良好｜順張り可。過熱なし。" not in html
    assert "AIテスト(1234)" in html
    assert "崩れスコア" in html
    assert "前日VWAP維持" not in html
    assert "<td>2</td>" in html


def test_technical_summary_html_renders_us_market_section():
    table = TechnicalSummaryTable(
        rows=(),
        us_market=UsMarketSummaryTable(
            as_of=datetime(2026, 6, 17, 9, 0),
            rows=(
                UsMarketSummaryRow(
                    name="NASDAQ総合",
                    ticker="^IXIC",
                    latest=100.0,
                    day_change_pct=1.2,
                    dev5_pct=2.3,
                    dev25_pct=4.5,
                    rsi14=55.6,
                ),
            ),
        ),
    )

    html = build_technical_summary_html(table)

    assert "US Market 2026-06-17 09:00" in html
    assert "NASDAQ総合" in html
    assert "+4.5%" in html


def _summary_row(
    *,
    name: str,
    code4: str,
    rank: str,
    collapse_risk_score: int,
) -> TechnicalSummaryRow:
    return TechnicalSummaryRow(
        name=name,
        code4=code4,
        rank=rank,
        rank_label="",
        latest=100.0,
        day_change_price=0.0,
        day_change_pct=0.0,
        three_session_change_pct=0.0,
        day_high=101.0,
        day_low=99.0,
        day_close_position=0.5,
        day_range_atr=1.0,
        vwap=100.0,
        vwap_diff_pct=0.0,
        dev25_pct=6.0,
        ma25_distance_atr=1.0,
        volume_vs_avg20_pct=100.0,
        previous_vwap_maintained=None,
        support_lines=(),
        resistance_lines=(),
        recent60_range_position=0.5,
        collapse_risk_score=collapse_risk_score,
    )
