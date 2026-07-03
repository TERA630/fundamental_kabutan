import pandas as pd

from app.domain.models.rsi_analysis import RsiDivergence, RsiSignal
from app.domain.policies.rsi_analysis import (
    build_rsi_divergence,
    classify_rsi_level,
    classify_rsi_overall,
)


def _signal(label: str) -> RsiSignal:
    return RsiSignal(
        value=50.0,
        delta=0.0,
        direction_symbol="→",
        direction_label="横ばい",
        level_label=label,
    )


def test_classify_rsi_level_uses_spec_priority_order():
    assert classify_rsi_level(75.0, -5.0) == "過熱後半"
    assert classify_rsi_level(70.0, 3.0) == "やや過熱"
    assert classify_rsi_level(62.0, 3.0) == "勢い良好"
    assert classify_rsi_level(50.0, 3.0) == "勢い改善"
    assert classify_rsi_level(61.0, 0.5) == "高止まり"
    assert classify_rsi_level(68.0, -2.0) == "勢い鈍化"
    assert classify_rsi_level(44.0, -2.0) == "反発弱い"
    assert classify_rsi_level(38.0, 2.0) == "底打ち初動"
    assert classify_rsi_level(29.9, 5.0) == "売られ過ぎ"
    assert classify_rsi_level(44.0, 0.0) == "中立"


def test_classify_rsi_overall_prioritizes_hourly_warning_divergence():
    overall = classify_rsi_overall(
        five_min_signal=_signal("勢い良好"),
        hourly_signal=_signal("勢い良好"),
        five_min_divergence=RsiDivergence("明確な乖離なし", ""),
        hourly_divergence=RsiDivergence("上昇鈍化", "価格高値更新 / RSI未更新"),
    )

    assert overall == "上昇鈍化警戒"


def test_classify_rsi_overall_treats_hourly_bottoming_divergence_as_start():
    overall = classify_rsi_overall(
        five_min_signal=_signal("中立"),
        hourly_signal=_signal("売られ過ぎ"),
        five_min_divergence=RsiDivergence("明確な乖離なし", ""),
        hourly_divergence=RsiDivergence("底打ち兆候", "価格安値更新 / RSI安値切上げ"),
    )

    assert overall == "底打ち初動"


def test_build_rsi_divergence_detects_price_high_without_rsi_high(monkeypatch):
    index = pd.date_range("2026-01-01 09:00", periods=25, freq="5min")
    high = pd.Series(
        [
            100,
            101,
            102,
            103,
            104,
            105,
            106,
            107,
            108,
            109,
            120,
            110,
            109,
            108,
            109,
            110,
            111,
            112,
            121,
            113,
            112,
            111,
            110,
            109,
            108,
        ],
        index=index,
        dtype=float,
    )
    rsi = pd.Series(
        [
            40,
            42,
            44,
            46,
            48,
            50,
            52,
            54,
            56,
            58,
            70,
            60,
            58,
            56,
            57,
            58,
            59,
            60,
            71,
            61,
            60,
            59,
            58,
            57,
            56,
        ],
        index=index,
        dtype=float,
    )
    frame = pd.DataFrame(
        {
            "Open": high - 1,
            "High": high,
            "Low": high - 6,
            "Close": high - 2,
            "Volume": 1000.0,
        },
        index=index,
    )
    monkeypatch.setattr("app.domain.policies.rsi_analysis.calc_rsi14", lambda _close: rsi)

    divergence = build_rsi_divergence(frame)

    assert divergence.label == "上昇鈍化"
    assert divergence.detail == "価格高値更新 / RSI未更新"
