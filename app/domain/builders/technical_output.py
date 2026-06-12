"""Builder for technical analysis text output."""

from __future__ import annotations

from app.domain.policies.technical_indicators import label_recent60_range_position_detail, label_volume_vs_avg20
from app.domain.usecases.technical_analysis import TechnicalAnalysisResult


def build_technical_output(result: TechnicalAnalysisResult) -> str:
    snapshot = result.snapshot
    lines = [
        f"【銘柄】{result.name} ({result.code4})",
        _format_opening_summary(result),
        "",
        "■当日位置・レンジ",
        f"始値：{_fmt_price(snapshot.price.open)}",
        f"高値：{_fmt_price(snapshot.price.high)}",
        f"安値：{_fmt_price(snapshot.price.low)}",
        f"終値：{_fmt_price(snapshot.price.close)}",
        f"当日値幅：{_fmt_price(snapshot.range.day_range)}（ATR比 {_fmt_multiple(snapshot.range.day_range_atr)} / {snapshot.range.day_range_label}）",
        "",
        "■移動平均",
        f"5日線：{_fmt_price(snapshot.moving_average.ma5)}（乖離 {_fmt_pct(snapshot.moving_average.dev5_pct)}）",
        f"25日線：{_fmt_price(snapshot.moving_average.ma25)}（乖離 {_fmt_pct(snapshot.moving_average.dev25_pct)} / ATR比 {_fmt_multiple(snapshot.moving_average.ma25_distance_atr)}）",
        f"14日ATR：{_fmt_price(snapshot.range.atr14)}",
        "",
        _format_previous_session(result),
        "",
        "■支持線",
        f"前日安値：{_fmt_price(snapshot.previous_session.prev_low)}",
        f"20日安値：{_fmt_price(snapshot.breakline.recent20_low)}",
        f"60日安値：{_fmt_price(snapshot.breakline.recent60_low)}",
    ]
    return "\n".join(lines) + "\n"


def _format_opening_summary(result: TechnicalAnalysisResult) -> str:
    snapshot = result.snapshot
    vwap_snapshot = result.vwap_snapshot
    momentum = result.three_session_momentum
    latest = snapshot.price.latest
    vwap = _as_float(vwap_snapshot.get("vwap"))
    vwap_diff = latest - vwap if latest is not None and vwap is not None else None
    vwap_diff_pct = ((latest / vwap) - 1) * 100 if latest is not None and vwap not in (None, 0) else None
    vwap_diff_atr = _safe_div(vwap_diff, snapshot.range.atr14)
    vwap_source_suffix = " (日足参考値)" if vwap_snapshot.get("vwap_source") == "日足参考値" else ""
    sessions = momentum.sessions
    volume_vs_avg20_pct = _ratio_pct(snapshot.price.volume, snapshot.price.volume_avg20)
    lines = [
        f"株価：{_fmt_price_current(latest)}円（前日比{_fmt_price_signed(snapshot.price.day_change_price)}円：{_fmt_pct(snapshot.price.day_change_pct)}）（終端位置{_fmt_position_pct(snapshot.range.day_close_position)}）",
        f"取得時刻：{_fmt_text(result.intraday_price_timestamp)}",
        f"25日線解離：{_fmt_pct(snapshot.moving_average.dev25_pct)}({_fmt_atr_distance(snapshot.moving_average.ma25_distance_atr)})　傾き：{_ma25_slope_symbol(result)}",
        f"Vwap：{_fmt_price_signed(vwap_diff)}円({_fmt_pct(vwap_diff_pct)}/{_fmt_atr(vwap_diff_atr)}){vwap_source_suffix}",
        *_format_current_session_vwap_lines(vwap_snapshot),
        f"当日出来高：20日平均比　{_fmt_pct_unsigned_no_decimal(volume_vs_avg20_pct)}(前日出来高比　{_fmt_pct(snapshot.price.volume_vs_previous_pct)})　{label_volume_vs_avg20(volume_vs_avg20_pct)}",
        f"60日レンジ位置：{_fmt_position_pct(snapshot.breakline.recent60_range_position)}　{label_recent60_range_position_detail(snapshot.breakline.recent60_range_position)}",
        "",
        "■モメンタム",
        f"3日高値更新：{_fmt_momentum_marks(session.high_breakout for session in sessions)}",
        f"3日安値切り上げ：{_fmt_momentum_marks(session.low_higher for session in sessions)}",
        f"3日騰落率　{_fmt_pct(momentum.change_pct)}",
        f"3日出来高　{_fmt_momentum_volumes(session.volume_vs_avg20_pct for session in sessions)}",
    ]
    return "\n".join(lines)


def _format_previous_session(result: TechnicalAnalysisResult) -> str:
    snapshot = result.snapshot
    previous = snapshot.previous_session
    intraday = result.previous_intraday_snapshot
    prev_close = snapshot.price.prev_close
    prev_vwap = _as_float(intraday.get("prev_vwap"))
    prev_vwap_diff = prev_close - prev_vwap if prev_close is not None and prev_vwap is not None else None
    prev_vwap_diff_pct = ((prev_close / prev_vwap) - 1) * 100 if prev_close is not None and prev_vwap not in (None, 0) else None
    prev_vwap_diff_atr = _safe_div(prev_vwap_diff, snapshot.range.atr14)
    pm_evaluation = intraday.get("previous_pm_evaluation")
    pm_vwap_position = intraday.get("previous_pm_vwap_position")
    return "\n".join(
        [
            "■前日評価",
            f"終値 {_fmt_price_compact(prev_close)}（VWAP {_fmt_price_signed_compact(prev_vwap_diff)}円 / {_fmt_pct(prev_vwap_diff_pct)} / {_fmt_atr_unsigned(prev_vwap_diff_atr)}）騰落率{_fmt_pct(previous.prev_change_pct)}",
            "",
            f"前日Vwap(前・後場)　{_fmt_bool_mark(_as_bool(intraday.get('prev_am_vwap_maintained')))}/{_fmt_bool_mark(_as_bool(intraday.get('prev_pm_vwap_maintained')))}  高値更新 {_fmt_bool_mark(previous.prev_high_higher)} / 安値維持 {_fmt_bool_mark(previous.prev_low_higher)}",
            f"前日出来高：　20日平均比　{_fmt_pct_unsigned(previous.prev_volume_vs_avg20_pct)}(前々日比　{_fmt_pct(previous.prev_volume_change_pct)})",
            "",
            f"後場評価 {_fmt_text(pm_evaluation)} / VWAP{_fmt_text(pm_vwap_position)}",
            "",
            f"前日レンジ {_fmt_price_compact(previous.prev_low)}-{_fmt_price_compact(previous.prev_high)}（{_fmt_atr_unsigned(previous.prev_range_atr)}）　終位置 {_fmt_position_pct(previous.prev_close_position)}",
            f"前日ローソク足型：　{_format_previous_candle(previous.candle_body_label, previous.wick_label)}",
        ]
    )


def _format_previous_candle(candle_body_label: str, wick_label: str) -> str:
    return candle_body_label if not wick_label else f"{candle_body_label}＋{wick_label}"


def _as_float(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _as_bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def _safe_div(numerator: float | int | None, denominator: float | int | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return float(numerator) / float(denominator)


def _ratio_pct(numerator: float | int | None, denominator: float | int | None) -> float | None:
    ratio = _safe_div(numerator, denominator)
    return None if ratio is None else ratio * 100


def _range_position(latest: float | None, low: float | None, high: float | None) -> float | None:
    width = high - low if high is not None and low is not None else None
    return _safe_div(latest - low, width) if latest is not None and low is not None else None


def _fmt_number(value: float | None, digits: int = 1) -> str:
    return "N/A" if value is None else f"{value:.{digits}f}"


def _fmt_price(value: float | None) -> str:
    return "N/A" if value is None else f"{value:,.2f}"


def _fmt_price_compact(value: float | None) -> str:
    if value is None:
        return "N/A"
    if float(value).is_integer():
        return f"{value:,.0f}"
    return f"{value:,.2f}"


def _fmt_price_current(value: float | None) -> str:
    if value is None:
        return "N/A"
    if abs(value) >= 1000:
        return f"{value:,.0f}"
    return f"{value:,.1f}"


def _fmt_price_signed(value: float | None) -> str:
    return "N/A" if value is None else f"{value:+,.2f}"


def _fmt_price_signed_compact(value: float | None) -> str:
    if value is None:
        return "N/A"
    if float(value).is_integer():
        return f"{value:+,.0f}"
    return f"{value:+,.2f}"


def _fmt_pct(value: float | None) -> str:
    return "N/A" if value is None else f"{value:+.1f}%"


def _fmt_pct_unsigned(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.1f}%"


def _fmt_pct_unsigned_no_decimal(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.0f}%"


def _fmt_position_pct(value: float | None) -> str:
    return "N/A" if value is None else f"{value * 100:.1f}%"


def _fmt_multiple(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2f}倍"


def _fmt_atr(value: float | None) -> str:
    return "N/A" if value is None else f"{value:+.2f}ATR"


def _fmt_atr_distance(value: float | None) -> str:
    return "N/A" if value is None else f"{abs(value):.2f}ATR"


def _fmt_atr_unsigned(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2f}ATR"


def _fmt_volume(value: float | None) -> str:
    return "N/A" if value is None else f"{value:,.0f}株"


def _fmt_volume_ratio(volume: float | None, average: float | None) -> str:
    ratio = _safe_div(volume, average)
    return "N/A" if ratio is None else f"{ratio * 100:.0f}%"


def _fmt_bool_mark(value: bool | None) -> str:
    if value is None:
        return "N/A"
    return "〇" if value else "×"


def _fmt_momentum_marks(values: object) -> str:
    return "".join(_fmt_bool_mark(_as_bool(value)) for value in values)


def _fmt_momentum_volumes(values: object) -> str:
    return "→".join(_fmt_volume_pct(value) for value in values)


def _fmt_volume_pct(value: object) -> str:
    number = _as_float(value)
    return "N/A" if number is None else f"{number:.0f}%"


def _fmt_text(value: object) -> str:
    return value if isinstance(value, str) and value else "N/A"


def _format_current_session_vwap_lines(vwap_snapshot: dict[str, object]) -> list[str]:
    if vwap_snapshot.get("vwap_source") != "本日5分足":
        return []
    session = vwap_snapshot.get("current_intraday_session")
    lines = [f"前場Vwap：{_fmt_price(_as_float(vwap_snapshot.get('current_am_vwap')))}"]
    if session == "後場":
        lines.append(f"後場Vwap：{_fmt_price(_as_float(vwap_snapshot.get('current_pm_vwap')))}")
    return lines


def _format_previous_high_evaluation(result: TechnicalAnalysisResult) -> str:
    snapshot = result.snapshot
    latest = snapshot.price.latest
    prev_high = snapshot.previous_session.prev_high
    prev_low = snapshot.previous_session.prev_low
    if latest is None or prev_high is None or prev_low is None:
        return "N/A"
    if latest > prev_high:
        return f"前日高値突破：{_fmt_pct(_pct_change(latest, prev_high))}"
    if latest >= prev_low:
        position = _range_position(latest, prev_low, prev_high)
        return f"前日レンジ：{_fmt_position_pct(position)}（{_range_position_label_middle(position)}）"
    return f"前日安値：{_fmt_pct(_pct_change(latest, prev_low))}"


def _pct_change(current: float | int | None, previous: float | int | None) -> float | None:
    ratio = _safe_div(current, previous)
    if ratio is None:
        return None
    return (ratio - 1) * 100


def _fmt_high_remaining_pct(distance_pct: float | None) -> str:
    if distance_pct is None:
        return "N/A"
    if distance_pct >= 0:
        return f"突破 {_fmt_pct(distance_pct)}"
    return f"{abs(distance_pct):.1f}%"


def _ma25_slope_symbol(result: TechnicalAnalysisResult) -> str:
    ma25 = result.snapshot.moving_average.ma25
    ma25_prev5 = result.snapshot.moving_average.ma25_prev5
    if ma25 is None or ma25_prev5 is None:
        return "N/A"
    if ma25 > ma25_prev5:
        return "↑"
    if ma25 < ma25_prev5:
        return "↓"
    return "→"


def _short_close_position_label(label: str) -> str:
    if label == "高値圏で終了":
        return "高値圏"
    if label == "中段で終了":
        return "中間"
    if label == "安値圏で終了":
        return "安値圏"
    return ""


def _range_position_label_middle(value: float | None) -> str:
    if value is None:
        return "N/A"
    if value >= 0.60:
        return "高値圏"
    if value >= 0.30:
        return "中間"
    return "安値圏"


def _short_trend_label(trend: str) -> str:
    if trend == "上昇トレンド":
        return "上昇"
    if trend == "下落トレンド":
        return "下落"
    if trend == "N/A":
        return "N/A"
    return "もみあい"


__all__ = ["build_technical_output"]
