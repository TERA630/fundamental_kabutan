"""Builder for technical analysis text output."""

from __future__ import annotations

from app.domain.models.technical_summary import TechnicalSummaryLine
from app.domain.policies.technical_summary import (
    build_d1_detail,
    build_d3_detail,
    build_d_detail_headline,
    build_technical_headline_summary,
    build_technical_position_assessment,
    build_technical_strategy_lines,
    build_nearby_support_lines,
    is_focus_theme,
)
from app.domain.usecases.technical_analysis import TechnicalAnalysisResult


def build_technical_output(result: TechnicalAnalysisResult) -> str:
    snapshot = result.snapshot
    lines = [
        _format_opening_summary(result),
        "",
        _format_headline_summary(result),
        _format_position_assessment(result),
        "",
        _format_strategy_assessment(result),
        "",
        _format_momentum(result),
        "",
        "■当日位置・レンジ",
        f"O {_fmt_price(_evaluation_open(result))}　H {_fmt_price(_evaluation_high(result))}　L {_fmt_price(_evaluation_low(result))}　C {_fmt_price(_evaluation_price(result))}",
        f"当日値幅：{_fmt_price(_evaluation_day_range(result))}（ATR比 {_fmt_multiple(_safe_div(_evaluation_day_range(result), snapshot.range.atr14))} / {snapshot.range.day_range_label}）",
        "",
        "■移動平均・Vwap",
        *_format_current_session_vwap_price_lines(result.vwap_snapshot),
        f"5日線：{_fmt_price(snapshot.moving_average.ma5)}（乖離 {_fmt_pct(snapshot.moving_average.dev5_pct)}）",
        f"25日線：{_fmt_price(snapshot.moving_average.ma25)}（乖離 {_fmt_pct(snapshot.moving_average.dev25_pct)} / ATR比 {_fmt_multiple(snapshot.moving_average.ma25_distance_atr)}）",
        f"14日ATR：{_fmt_price(snapshot.range.atr14)}",
        "",
        _format_previous_session(result),
    ]
    return "\n".join(lines) + "\n"


def _format_resistance_lines(result: TechnicalAnalysisResult) -> list[str]:
    lines = _build_resistance_lines(result)
    if not lines:
        return ["N/A"]
    return [f"{line.label}：{_fmt_price(line.price)}" for line in lines]


def _build_resistance_lines(result: TechnicalAnalysisResult) -> tuple[TechnicalSummaryLine, ...]:
    snapshot = result.snapshot
    latest = _evaluation_price(result)
    if latest is None:
        return ()

    candidates = (
        TechnicalSummaryLine("前日高値", snapshot.previous_session.prev_high)
        if snapshot.previous_session.prev_high is not None
        else None,
        TechnicalSummaryLine("25日線", snapshot.moving_average.ma25)
        if snapshot.moving_average.ma25 is not None
        else None,
        TechnicalSummaryLine("20日高値", snapshot.breakline.recent20_high)
        if snapshot.breakline.recent20_high is not None
        else None,
        TechnicalSummaryLine("60日高値", snapshot.breakline.recent60_high)
        if snapshot.breakline.recent60_high is not None
        else None,
    )
    above = [line for line in candidates if line is not None and line.price > latest]
    return tuple(sorted(above, key=lambda line: line.price))


def _format_opening_summary(result: TechnicalAnalysisResult) -> str:
    snapshot = result.snapshot
    vwap_snapshot = result.vwap_snapshot
    latest = _evaluation_price(result)
    vwap = _as_float(vwap_snapshot.get("vwap"))
    vwap_diff = latest - vwap if latest is not None and vwap is not None else None
    vwap_diff_pct = ((latest / vwap) - 1) * 100 if latest is not None and vwap not in (None, 0) else None
    vwap_diff_atr = _safe_div(vwap_diff, snapshot.range.atr14)
    vwap_source_suffix = " (日足参考値)" if vwap_snapshot.get("vwap_source") == "日足参考値" else ""
    volume_vs_avg20_pct = _ratio_pct(_evaluation_volume(result), snapshot.price.volume_avg20)
    lines = [
        f"取得時刻：{_fmt_text(result.evaluation_price_timestamp)}",
        f"【銘柄】{result.name} ({result.code4})",
        f"　株価：{_fmt_price_current(latest)}円（前日比{_fmt_price_signed(_price_change(result))}円：{_fmt_pct(_price_change_pct(result))}）（終端位置{_fmt_position_pct(_range_position(latest, _evaluation_low(result), _evaluation_high(result)))}）"
        f" | 出来高比　{_fmt_pct_unsigned_no_decimal(volume_vs_avg20_pct)}(前日比{_fmt_pct(snapshot.price.volume_vs_previous_pct)})",
        f"　位置：25日線{_fmt_pct(_evaluation_dev25_pct(result))}/{_fmt_atr_distance(_evaluation_ma25_distance_atr(result))}"
        f" | VWAP{_fmt_price_signed(vwap_diff)}円/{_fmt_pct(vwap_diff_pct)}/{_fmt_atr_distance(vwap_diff_atr)}{vwap_source_suffix}"
        f" | 60日レンジ　{_fmt_position_pct(snapshot.breakline.recent60_range_position)} |",
        f"　下値目安：{_format_opening_supports(result)}",
        f"　抵抗：{_format_opening_resistances(result)}",
        f"　需給（VWAP）：{_format_vwap_supply_marks(result)}",
    ]
    return "\n".join(lines)


def _format_opening_supports(result: TechnicalAnalysisResult) -> str:
    snapshot = result.snapshot
    latest = _evaluation_price(result)
    if latest is None:
        return "N/A"
    candidates = (
        ("preL", snapshot.previous_session.prev_low),
        ("25ME", snapshot.moving_average.ma25),
        ("20dL", snapshot.breakline.recent20_low),
        ("60dL", snapshot.breakline.recent60_low),
        ("75ME", snapshot.moving_average.ma75),
    )
    return _format_grouped_price_levels(candidates, latest=latest, ascending=False, max_levels=3)


def _format_opening_resistances(result: TechnicalAnalysisResult) -> str:
    snapshot = result.snapshot
    latest = _evaluation_price(result)
    if latest is None:
        return "N/A"
    candidates = (
        ("preH", snapshot.previous_session.prev_high),
        ("25ME", snapshot.moving_average.ma25),
        ("20dH", snapshot.breakline.recent20_high),
        ("60dH", snapshot.breakline.recent60_high),
    )
    return _format_grouped_price_levels(candidates, latest=latest, ascending=True)


def _format_grouped_price_levels(
    candidates: tuple[tuple[str, float | None], ...],
    *,
    latest: float,
    ascending: bool,
    max_levels: int | None = None,
) -> str:
    grouped: dict[float, list[str]] = {}
    for label, price in candidates:
        if price is None or (price <= latest if ascending else price >= latest):
            continue
        grouped.setdefault(price, []).append(label)
    if not grouped:
        return "N/A"
    prices = sorted(grouped, reverse=not ascending)
    if max_levels is not None:
        prices = prices[:max_levels]
    return "→".join(
        f"{_fmt_level_price(price)}({'/'.join(grouped[price])})"
        for price in prices
    )


def _format_headline_summary(result: TechnicalAnalysisResult) -> str:
    headline = _build_headline(result)
    if headline is None:
        return "短評：N/A"
    detail_headline = build_d_detail_headline(
        headline.rank,
        ma25_distance_atr=_evaluation_ma25_distance_atr(result),
        volume_vs_avg20_pct=_ratio_pct(
            _evaluation_volume(result),
            result.snapshot.price.volume_avg20,
        ),
        dev25_pct=_evaluation_dev25_pct(result),
    )
    return f"短評：{detail_headline or headline.text}"


def _format_position_assessment(result: TechnicalAnalysisResult) -> str:
    snapshot = result.snapshot
    latest = _evaluation_price(result)
    vwap = _as_float(result.vwap_snapshot.get("vwap"))
    ma25 = snapshot.moving_average.ma25
    dev25_pct = _evaluation_dev25_pct(result)
    if latest is None or vwap is None or ma25 is None or dev25_pct is None:
        return "崩れ警戒：N/A\nホールド判定：N/A"

    headline = _build_headline(result)
    if headline is None:
        return "崩れ警戒：N/A\nホールド判定：N/A"
    assessment = build_technical_position_assessment(
        latest=latest,
        vwap=vwap,
        ma25=ma25,
        atr14=snapshot.range.atr14,
        day_open=_evaluation_open(result),
        day_high=_evaluation_high(result),
        day_low=_evaluation_low(result),
        day_close_position=_range_position(latest, _evaluation_low(result), _evaluation_high(result)),
        volume_vs_avg20_pct=_ratio_pct(_evaluation_volume(result), snapshot.price.volume_avg20),
        high_breakouts=tuple(session.high_breakout for session in result.three_session_momentum.sessions),
        low_highers=tuple(session.low_higher for session in result.three_session_momentum.sessions),
        previous_low=snapshot.previous_session.prev_low,
        recent20_low=snapshot.breakline.recent20_low,
        ma75=snapshot.moving_average.ma75,
        recent60_low=snapshot.breakline.recent60_low,
        headline_rank=headline.rank,
    )
    lines = [
        f"崩れ警戒：{assessment.collapse_risk_level}（{assessment.collapse_risk_score}点）",
    ]
    if latest < ma25:
        established = "成立" if assessment.bottoming_start_established else "未成立"
        lines.append(f"底打ち初動判定：{established}")
    lines.append(f"ホールド判定：{assessment.hold_judgement}")
    return "\n".join(lines)


def _format_strategy_assessment(result: TechnicalAnalysisResult) -> str:
    snapshot = result.snapshot
    latest = _evaluation_price(result)
    vwap = _as_float(result.vwap_snapshot.get("vwap"))
    dev25_pct = _evaluation_dev25_pct(result)
    if latest is None or vwap is None or dev25_pct is None:
        return "戦略判定：\nN/A"

    headline = _build_headline(result)
    if headline is None:
        return "戦略判定：\nN/A"
    supports = build_nearby_support_lines(
        latest=latest,
        ma25=snapshot.moving_average.ma25,
        previous_low=snapshot.previous_session.prev_low,
        recent20_low=snapshot.breakline.recent20_low,
        ma75=snapshot.moving_average.ma75,
        recent60_low=snapshot.breakline.recent60_low,
    )
    support_prices = sorted(line.price for line in supports)
    support_range = "〜".join(_fmt_price_compact(price) for price in support_prices) or "N/A"
    nearest_support = _fmt_price_compact(supports[0].price) if supports else "N/A"
    detail_code = _strategy_detail_code(result, headline.rank)
    atr14 = snapshot.range.atr14
    support_price = supports[0].price if supports else None
    support_entry_range = _fmt_strategy_band(
        support_price,
        _offset_price(support_price, atr14, 0.15),
    )
    support_pullback_range = _fmt_strategy_band(
        support_price,
        _offset_price(support_price, atr14, 0.25),
    )
    vwap_recovery_range = _fmt_strategy_band(vwap, _offset_price(vwap, atr14, 0.20))
    vwap_pullback_range = _fmt_strategy_band(_offset_price(vwap, atr14, -0.25), vwap)
    rr_entry_offset = 0.25 if headline.rank == "D3" else 0.15
    rr_entry = _offset_price(support_price, atr14, rr_entry_offset)
    rr_stop = _offset_price(support_price, atr14, -0.35)
    rr_target = _nearest_target_above(rr_entry, _build_resistance_lines(result))
    risk_reward = _fmt_risk_reward(_calculate_risk_reward(rr_entry, rr_stop, rr_target))
    strategy_lines = build_technical_strategy_lines(
        headline.rank,
        support_range=support_range,
        nearest_support=nearest_support,
        detail_code=detail_code,
        support_entry_range=support_entry_range,
        support_pullback_range=support_pullback_range,
        vwap_recovery_range=vwap_recovery_range,
        vwap_pullback_range=vwap_pullback_range,
        risk_reward=risk_reward,
    )
    return "\n".join(("戦略判定：", *strategy_lines))


def _strategy_detail_code(result: TechnicalAnalysisResult, rank: str) -> str | None:
    if rank == "D1":
        return build_d1_detail(ma25_distance_atr=_evaluation_ma25_distance_atr(result))[0]
    if rank == "D3":
        return build_d3_detail(
            volume_vs_avg20_pct=_ratio_pct(
                _evaluation_volume(result),
                result.snapshot.price.volume_avg20,
            )
        )[0]
    return rank if rank == "D2" else None


def _offset_price(price: float | None, atr14: float | None, multiple: float) -> float | None:
    if price is None or atr14 is None:
        return None
    return price + atr14 * multiple


def _fmt_strategy_band(low: float | None, high: float | None) -> str:
    if low is None or high is None:
        return "指値算出不可"
    return f"{_fmt_price_compact(low)}〜{_fmt_price_compact(high)}円"


def _nearest_target_above(
    entry: float | None,
    lines: tuple[TechnicalSummaryLine, ...],
) -> float | None:
    if entry is None:
        return None
    targets = [line.price for line in lines if line.price > entry]
    return min(targets) if targets else None


def _calculate_risk_reward(
    entry: float | None,
    stop: float | None,
    target: float | None,
) -> float | None:
    if entry is None or stop is None or target is None:
        return None
    risk = entry - stop
    reward = target - entry
    if risk <= 0 or reward <= 0:
        return None
    return reward / risk


def _fmt_risk_reward(value: float | None) -> str:
    return "RR算出不可" if value is None else f"RR{value:.2f}"


def _format_momentum(result: TechnicalAnalysisResult) -> str:
    momentum = result.three_session_momentum
    sessions = momentum.sessions
    return "\n".join(
        [
            "■モメンタム",
            f"3日高値更新：{_fmt_momentum_marks(session.high_breakout for session in sessions)}",
            f"3日安値切り上げ：{_fmt_momentum_marks(session.low_higher for session in sessions)}",
            f"3日騰落率　{_fmt_pct(momentum.change_pct)}",
            f"3日出来高　{_fmt_momentum_volumes(session.volume_vs_avg20_pct for session in sessions)}",
        ]
    )


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
    return "\n".join(
        [
            "■前日評価",
            f"終値 {_fmt_price_compact(prev_close)}（VWAP {_fmt_price_signed_compact(prev_vwap_diff)}円 / {_fmt_pct(prev_vwap_diff_pct)} / {_fmt_atr_unsigned(prev_vwap_diff_atr)}）騰落率{_fmt_pct(previous.prev_change_pct)}",
            "",
            f"前日出来高：　20日平均比　{_fmt_pct_unsigned(previous.prev_volume_vs_avg20_pct)}(前々日比　{_fmt_pct(previous.prev_volume_change_pct)})",
            "",
            f"後場評価 {_fmt_text(pm_evaluation)}",
            "",
            f"前日レンジ {_fmt_price_compact(previous.prev_low)}-{_fmt_price_compact(previous.prev_high)}（{_fmt_atr_unsigned(previous.prev_range_atr)}）　終位置 {_fmt_position_pct(previous.prev_close_position)}",
            f"前日ローソク足型：　{_format_previous_candle(previous.candle_body_label, previous.wick_label)}",
        ]
    )


def _format_previous_candle(candle_body_label: str, wick_label: str) -> str:
    return candle_body_label if not wick_label else f"{candle_body_label}＋{wick_label}"


def _build_headline(result: TechnicalAnalysisResult):
    snapshot = result.snapshot
    latest = _evaluation_price(result)
    vwap = _as_float(result.vwap_snapshot.get("vwap"))
    dev25_pct = _evaluation_dev25_pct(result)
    if latest is None or vwap is None or dev25_pct is None:
        return None
    sessions = result.three_session_momentum.sessions
    return build_technical_headline_summary(
        dev25_pct=dev25_pct,
        latest=latest,
        vwap=vwap,
        focus_theme=is_focus_theme(result.name),
        ma25_distance_atr=_evaluation_ma25_distance_atr(result),
        ma25=snapshot.moving_average.ma25,
        ma25_prev5=snapshot.moving_average.ma25_prev5,
        rsi14=snapshot.rsi14,
        three_session_change_pct=result.three_session_momentum.change_pct,
        high_breakout_count=_count_true(session.high_breakout for session in sessions),
        low_higher_count=_count_true(session.low_higher for session in sessions),
        day_close_position=_range_position(latest, _evaluation_low(result), _evaluation_high(result)),
        day_open=_evaluation_open(result),
        day_high=_evaluation_high(result),
        day_low=_evaluation_low(result),
        atr14=snapshot.range.atr14,
        volume_vs_avg20_pct=_ratio_pct(_evaluation_volume(result), snapshot.price.volume_avg20),
        recent60_range_position=snapshot.breakline.recent60_range_position,
        previous_low=snapshot.previous_session.prev_low,
        recent20_low=snapshot.breakline.recent20_low,
        ma75=snapshot.moving_average.ma75,
        recent60_low=snapshot.breakline.recent60_low,
        vwap_maintained_15m=_as_bool(result.vwap_snapshot.get("vwap_maintained_15m")),
        low_highers=tuple(session.low_higher for session in sessions),
    )


def _evaluation_price(result: TechnicalAnalysisResult) -> float | None:
    value = getattr(result, "evaluation_price", None)
    return _as_float(value) if value is not None else result.snapshot.price.latest


def _evaluation_open(result: TechnicalAnalysisResult) -> float | None:
    return _evaluation_intraday_field(result, "open", result.snapshot.price.open)


def _evaluation_high(result: TechnicalAnalysisResult) -> float | None:
    return _evaluation_intraday_field(result, "high", result.snapshot.price.high)


def _evaluation_low(result: TechnicalAnalysisResult) -> float | None:
    return _evaluation_intraday_field(result, "low", result.snapshot.price.low)


def _evaluation_volume(result: TechnicalAnalysisResult) -> float | None:
    return _evaluation_intraday_field(result, "volume", result.snapshot.price.volume)


def _evaluation_day_range(result: TechnicalAnalysisResult) -> float | None:
    high = _evaluation_high(result)
    low = _evaluation_low(result)
    return high - low if high is not None and low is not None else None


def _evaluation_intraday_field(
    result: TechnicalAnalysisResult,
    key: str,
    daily_value: float | None,
) -> float | None:
    source = getattr(result, "evaluation_price_source", "daily_close")
    if source in {"intraday_5m", "provisional_close"}:
        value = _as_float(result.vwap_snapshot.get(key))
        if value is not None:
            return value
    return daily_value


def _evaluation_dev25_pct(result: TechnicalAnalysisResult) -> float | None:
    return _pct_change(_evaluation_price(result), result.snapshot.moving_average.ma25)


def _evaluation_ma25_distance_atr(result: TechnicalAnalysisResult) -> float | None:
    latest = _evaluation_price(result)
    ma25 = result.snapshot.moving_average.ma25
    distance = latest - ma25 if latest is not None and ma25 is not None else None
    return _safe_div(distance, result.snapshot.range.atr14)


def _price_change(result: TechnicalAnalysisResult) -> float | None:
    latest = _evaluation_price(result)
    previous = result.snapshot.price.prev_close
    return latest - previous if latest is not None and previous is not None else None


def _price_change_pct(result: TechnicalAnalysisResult) -> float | None:
    return _pct_change(_evaluation_price(result), result.snapshot.price.prev_close)


def _as_float(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _as_bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def _count_true(values: object) -> int:
    return sum(1 for value in values if value is True)


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


def _fmt_level_price(value: float) -> str:
    if float(value).is_integer():
        return f"{value:.0f}"
    return f"{value:.2f}"


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


def _format_vwap_supply_marks(result: TechnicalAnalysisResult) -> str:
    current = result.vwap_snapshot
    previous = result.previous_intraday_snapshot
    latest = _evaluation_price(result)
    session = current.get("current_intraday_session")

    if current.get("vwap_source") != "本日5分足":
        current_text = "当日 N/A"
    elif session == "後場":
        current_text = (
            "当日前場／後場　"
            f"{_fmt_vwap_mark(latest, _as_float(current.get('current_am_vwap')))}／"
            f"{_fmt_vwap_mark(latest, _as_float(current.get('current_pm_vwap')))}"
        )
    else:
        current_text = (
            "当日前場　"
            f"{_fmt_vwap_mark(latest, _as_float(current.get('current_am_vwap')))}"
        )

    previous_text = (
        "前日前場／後場　"
        f"{_fmt_vwap_bool_mark(_as_bool(previous.get('prev_am_vwap_maintained')))}／"
        f"{_fmt_vwap_bool_mark(_as_bool(previous.get('prev_pm_vwap_maintained')))}"
    )
    return f"{current_text}　{previous_text}"


def _fmt_vwap_bool_mark(value: bool | None) -> str:
    if value is None:
        return "N/A"
    return "◯" if value else "×"


def _format_current_session_vwap_price_lines(vwap_snapshot: dict[str, object]) -> list[str]:
    if vwap_snapshot.get("vwap_source") != "本日5分足":
        return []
    session = vwap_snapshot.get("current_intraday_session")
    lines = [f"前場Vwap：{_fmt_price(_as_float(vwap_snapshot.get('current_am_vwap')))}"]
    if session == "後場":
        lines.append(f"後場Vwap：{_fmt_price(_as_float(vwap_snapshot.get('current_pm_vwap')))}")
    return lines


def _fmt_vwap_mark(latest: float | None, vwap: float | None) -> str:
    if latest is None or vwap is None:
        return "N/A"
    return "◯" if latest >= vwap else "×"


def _format_previous_high_evaluation(result: TechnicalAnalysisResult) -> str:
    snapshot = result.snapshot
    latest = _evaluation_price(result)
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
