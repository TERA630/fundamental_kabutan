import pandas as pd
import pytest

from app.domain.policies.technical_indicators import (
    build_technical_snapshot,
    calc_atr14,
    calc_rsi14,
    label_candle,
    label_candle_body,
    label_close_position,
    label_high_higher,
    label_low_higher,
    label_previous_wick,
    label_pullback,
    label_range_atr,
    label_range_position,
    label_trend,
    label_wick_shape,
    normalize_daily_history,
)


def _daily_history(rows: int = 70) -> pd.DataFrame:
    index = pd.date_range("2026-01-01", periods=rows, freq="B")
    close = pd.Series(range(100, 100 + rows), index=index, dtype=float)
    open_ = close - 1
    high = close + 2
    low = close - 3
    volume = pd.Series([1000 + i for i in range(rows)], index=index, dtype=float)
    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": volume,
        },
        index=index,
    )


def test_normalize_daily_history_requires_columns():
    with pytest.raises(ValueError):
        normalize_daily_history(pd.DataFrame({"Close": [1, 2, 3]}))


def test_calc_rsi14_and_atr14_return_values_after_warmup():
    history = _daily_history()

    rsi = calc_rsi14(history["Close"])
    atr = calc_atr14(history)

    assert rsi.iloc[-1] == pytest.approx(100.0)
    assert atr.iloc[-1] == pytest.approx(5.0)


def test_build_technical_snapshot_from_daily_history():
    history = _daily_history()

    snapshot = build_technical_snapshot(history)

    assert snapshot.price.latest == 169.0
    assert snapshot.price.prev_close == 168.0
    assert snapshot.price.day_change_price == 1.0
    assert snapshot.price.day_change_pct == pytest.approx(0.595238)
    assert snapshot.moving_average.ma5 == pytest.approx(167.0)
    assert snapshot.moving_average.ma25 == pytest.approx(157.0)
    assert snapshot.moving_average.ma25_prev5 == pytest.approx(152.0)
    assert snapshot.moving_average.dev25_pct == pytest.approx(((169 / 157) - 1) * 100)
    assert snapshot.range.atr14 == pytest.approx(5.0)
    assert snapshot.range.day_range == 5.0
    assert snapshot.range.day_range_atr == pytest.approx(1.0)
    assert snapshot.range.day_range_label == "大きめ"
    assert snapshot.range.day_close_position == pytest.approx(0.6)
    assert snapshot.range.day_close_position_label == "高値圏で終了"
    assert snapshot.previous_session.candle == "陽線"
    assert snapshot.previous_session.candle_body_label == "小陽線"
    assert snapshot.previous_session.wick_label == ""
    assert snapshot.previous_session.prev_high_higher is True
    assert snapshot.previous_session.prev_low_higher is True
    assert snapshot.previous_session.prev_volume_vs_avg20_pct == pytest.approx(1068 / 1058.5 * 100)
    assert snapshot.previous_session.prev_volume_change_pct == pytest.approx((1068 / 1067 - 1) * 100)
    assert snapshot.previous_session.pullback in {"押し", "中立", "崩れ", "判定不可"}
    assert snapshot.breakline.recent5_high == pytest.approx(170.0)
    assert snapshot.breakline.recent20_high == pytest.approx(170.0)
    assert snapshot.breakline.recent60_high == pytest.approx(170.0)
    assert snapshot.breakline.recent60_low == pytest.approx(106.0)
    assert snapshot.breakline.recent60_range_position == pytest.approx((169 - 106) / (170 - 106))
    assert snapshot.breakline.recent60_range_position_label == "高値圏"
    assert snapshot.rsi14 == pytest.approx(100.0)
    assert snapshot.trend == "上昇トレンド"


def test_build_technical_snapshot_rejects_short_history():
    with pytest.raises(ValueError):
        build_technical_snapshot(_daily_history(29))


def test_label_boundaries():
    assert label_range_atr(None) == "N/A"
    assert label_range_atr(0.49) == "浅い値幅"
    assert label_range_atr(0.5) == "通常値幅"
    assert label_range_atr(1.0) == "大きめ"
    assert label_range_atr(1.5) == "急拡大"

    assert label_close_position(None) == "N/A"
    assert label_close_position(0.6) == "高値圏で終了"
    assert label_close_position(0.3) == "中段で終了"
    assert label_close_position(0.29) == "安値圏で終了"

    assert label_range_position(None) == "N/A"
    assert label_range_position(0.6) == "高値圏"
    assert label_range_position(0.3) == "中段"
    assert label_range_position(0.29) == "安値圏"


def test_candle_wick_trend_and_pullback_labels():
    assert label_candle(100, 101) == "陽線"
    assert label_candle(101, 100) == "陰線"
    assert label_candle(100, 100) == "十字線"

    assert label_wick_shape(100, 110, 99, 108) == "実体大きめ"
    assert label_wick_shape(105, 106, 95, 104) == "下ヒゲ長め"
    assert label_wick_shape(105, 115, 104, 106) == "上ヒゲ長め"
    assert label_wick_shape(100, 105, 98, 103) == "通常足"

    assert label_candle_body(100, 111, 99, 101) == "十字"
    assert label_candle_body(100, 106, 99, 102) == "小陽線"
    assert label_candle_body(103, 104, 97, 101) == "小陰線"
    assert label_candle_body(100, 106, 99, 104) == "陽線"
    assert label_candle_body(104, 105, 98, 100) == "陰線"
    assert label_candle_body(100, 106, 99, 105) == "大陽線"
    assert label_candle_body(105, 106, 99, 100) == "大陰線"
    assert label_candle_body(100, 100, 100, 100) == "N/A"

    assert label_previous_wick(100, 110, 99, 102) == "上髭"
    assert label_previous_wick(105, 106, 95, 103) == "下髭"
    assert label_previous_wick(100, 105, 95, 100) == ""
    assert label_previous_wick(100, 100, 100, 100) == "N/A"

    assert label_high_higher(110, 109) is True
    assert label_high_higher(110, 110) is False
    assert label_high_higher(None, 110) is None
    assert label_low_higher(100, 100) is True
    assert label_low_higher(99, 100) is False
    assert label_low_higher(100, None) is None

    assert label_trend(110, 105, 100, 99) == "上昇トレンド"
    assert label_trend(90, 95, 100, 101) == "下落トレンド"
    assert label_trend(100, 99, 101, 100) == "もみ合い / 戻り局面"
    assert label_trend(None, 99, 101, 100) == "N/A"

    assert label_pullback(None, 0.5, 0) == "判定不可"
    assert label_pullback(1.3, 0.3, 20) == "崩れ"
    assert label_pullback(1.5, 0.4, 0) == "崩れ"
    assert label_pullback(0.8, 0.45, 20) == "押し"
    assert label_pullback(0.2, 0.8, 100) == "中立"
