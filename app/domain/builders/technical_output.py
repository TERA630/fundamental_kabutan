"""Builder for technical analysis text output."""

from __future__ import annotations

from datetime import datetime, time

from app.domain.models.technical_summary import TechnicalSummaryLine
from app.domain.policies.technical_summary import (
    build_collapse_score_brief,
    build_d1_detail,
    build_d2_detail,
    build_d3_detail,
    build_technical_headline_summary,
    build_technical_position_assessment,
    build_technical_short_comment,
    build_technical_strategy_lines,
    build_nearby_support_lines,
)
from app.domain.usecases.technical_analysis import TechnicalAnalysisResult

RISK_REWARD_NEAR_ATR_MULTIPLE = 0.20
RISK_REWARD_NEAR_PCT = 0.3


def build_technical_output(result: TechnicalAnalysisResult) -> str:
    snapshot = result.snapshot
    lines = [
        _format_opening_summary(result),
        _format_rsi_analysis(result),
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
        "■重要価格",
        *_format_current_session_vwap_price_lines(result.vwap_snapshot),
        f"25日線：{_fmt_price(snapshot.moving_average.ma25)}",
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


def _format_rsi_analysis(result: TechnicalAnalysisResult) -> str:
    analysis = getattr(result, "rsi_analysis", None)
    if analysis is None:
        return "RSI：5分N/A / 時間N/A\nRSI総合：N/A"

    lines = [
        f"RSI：5分{_fmt_rsi_signal(analysis.five_min)} / 時間{_fmt_rsi_signal(analysis.hourly)}",
    ]
    divergence_parts = []
    if analysis.hourly_divergence.label not in {"明確な乖離なし", "N/A"}:
        divergence_parts.append(f"時間足 {analysis.hourly_divergence.label}")
    if analysis.five_min_divergence.label not in {"明確な乖離なし", "N/A"}:
        divergence_parts.append(f"5分足 {analysis.five_min_divergence.label}")
    if divergence_parts:
        lines.append(f"RSIダイバージェンス：{' / '.join(divergence_parts)}")
    lines.append(f"RSI総合：{analysis.overall_label}")
    return "\n".join(lines)


def _fmt_rsi_signal(signal) -> str:
    if signal.value is None:
        return "N/A"
    return f"{signal.value:.0f}{signal.direction_symbol} {signal.level_label}"


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
    vwap_diff_atr = _safe_div(vwap_diff, snapshot.range.atr14)
    vwap_source_suffix = " (日足参考値)" if vwap_snapshot.get("vwap_source") == "日足参考値" else ""
    volume_vs_avg20_pct = _ratio_pct(_evaluation_volume(result), snapshot.price.volume_avg20)
    lines = [
        f"取得時刻：{_fmt_text(result.evaluation_price_timestamp)}",
        f"【銘柄】{result.name} ({result.code4})",
        f"　株価：{_fmt_price_current(latest)}円（前日比{_fmt_price_signed(_price_change(result))}円：{_fmt_pct(_price_change_pct(result))}）（終端位置{_fmt_position_pct(_range_position(latest, _evaluation_low(result), _evaluation_high(result)))}）"
        f" | 出来高：20日平均比 {_fmt_pct_unsigned_no_decimal(volume_vs_avg20_pct)} / 前日比{_fmt_pct_ratio_no_decimal(snapshot.price.volume_vs_previous_pct)}",
        f"　位置：25日線{_fmt_pct(_evaluation_dev25_pct(result))}/{_fmt_atr_distance(_evaluation_ma25_distance_atr(result))}"
        f" | VWAP{_fmt_price_signed(vwap_diff)}円/{_fmt_atr_distance(vwap_diff_atr)}{vwap_source_suffix}"
        f" | {_format_current_session_vwap_position(result)}"
        f" | 60日レンジ　{_fmt_position_pct(snapshot.breakline.recent60_range_position)} |",
        f"　リスクリターン：{_format_current_risk_reward(result)}",
        f"　下値：{_format_opening_supports(result)}",
        f"　抵抗：{_format_opening_resistances(result)}",
        f"　需給（VWAP）：{_format_vwap_supply_marks(result)}",
    ]
    return "\n".join(lines)


def _format_opening_supports(result: TechnicalAnalysisResult) -> str:
    latest = _evaluation_price(result)
    if latest is None:
        return "N/A"
    return _format_grouped_price_levels_with_room(
        _opening_support_candidates(result),
        latest=latest,
        ascending=False,
        max_levels=3,
        direction="down",
    )


def _format_opening_resistances(result: TechnicalAnalysisResult) -> str:
    latest = _evaluation_price(result)
    if latest is None:
        return "N/A"
    return _format_grouped_price_levels_with_room(
        _opening_resistance_candidates(result),
        latest=latest,
        ascending=True,
        direction="up",
    )


def _format_current_session_vwap_position(result: TechnicalAnalysisResult) -> str:
    current = result.vwap_snapshot
    latest = _evaluation_price(result)
    targets = (
        ("前場VWAP", _as_float(current.get("current_am_vwap"))),
        ("後場VWAP", _as_float(current.get("current_pm_vwap"))),
    )
    return " ".join(
        f"{label}{_fmt_pct(_pct_distance_from_current(latest, value))}"
        for label, value in targets
    )


def _format_current_risk_reward(result: TechnicalAnalysisResult) -> str:
    latest = _evaluation_price(result)
    if latest in (None, 0):
        return "N/A"
    downside = _select_risk_reward_level(
        latest=latest,
        atr14=result.snapshot.range.atr14,
        levels=_opening_support_prices(result),
    )
    resistance = _select_risk_reward_level(
        latest=latest,
        atr14=result.snapshot.range.atr14,
        levels=_opening_resistance_prices(result),
    )
    if downside is None or resistance is None:
        return "N/A"
    risk = latest - downside
    reward = resistance - latest
    if risk <= 0 or reward <= 0:
        return "N/A"
    return f"RR{reward / risk:.2f}"


def _select_risk_reward_level(
    *,
    latest: float,
    atr14: float | None,
    levels: tuple[float, ...],
) -> float | None:
    for level in levels:
        if not _is_too_near_for_risk_reward(latest=latest, level=level, atr14=atr14):
            return level
    return None


def _is_too_near_for_risk_reward(
    *,
    latest: float,
    level: float,
    atr14: float | None,
) -> bool:
    distance = abs(latest - level)
    distance_pct = _safe_div(distance, latest)
    near_by_pct = distance_pct is not None and distance_pct * 100 < RISK_REWARD_NEAR_PCT
    near_by_atr = atr14 not in (None, 0) and distance < RISK_REWARD_NEAR_ATR_MULTIPLE * atr14
    return near_by_pct or near_by_atr


def _opening_support_prices(result: TechnicalAnalysisResult) -> tuple[float, ...]:
    latest = _evaluation_price(result)
    if latest is None:
        return ()
    return tuple(
        price
        for price, _labels in _group_price_levels(
            _opening_support_candidates(result),
            latest=latest,
            ascending=False,
        )
    )


def _opening_resistance_prices(result: TechnicalAnalysisResult) -> tuple[float, ...]:
    latest = _evaluation_price(result)
    if latest is None:
        return ()
    return tuple(
        price
        for price, _labels in _group_price_levels(
            _opening_resistance_candidates(result),
            latest=latest,
            ascending=True,
        )
    )


def _opening_support_candidates(result: TechnicalAnalysisResult) -> tuple[tuple[str, float | None], ...]:
    snapshot = result.snapshot
    return (
        ("preL", snapshot.previous_session.prev_low),
        ("25ME", snapshot.moving_average.ma25),
        ("20dL", snapshot.breakline.recent20_low),
        ("60dL", snapshot.breakline.recent60_low),
        ("75ME", snapshot.moving_average.ma75),
    )


def _opening_resistance_candidates(result: TechnicalAnalysisResult) -> tuple[tuple[str, float | None], ...]:
    snapshot = result.snapshot
    return (
        ("preH", snapshot.previous_session.prev_high),
        ("25ME", snapshot.moving_average.ma25),
        ("20dH", snapshot.breakline.recent20_high),
        ("60dH", snapshot.breakline.recent60_high),
    )


def _format_grouped_price_levels_with_room(
    candidates: tuple[tuple[str, float | None], ...],
    *,
    latest: float,
    ascending: bool,
    direction: str,
    max_levels: int | None = None,
) -> str:
    levels = _group_price_levels(candidates, latest=latest, ascending=ascending, max_levels=max_levels)
    if not levels:
        return "N/A"
    return "→".join(
        f"{_fmt_level_price(price)}({'/'.join(labels)})：{_fmt_pct_unsigned(_level_room_pct(price, latest, direction))}"
        for price, labels in levels
    )


def _level_room_pct(price: float, latest: float, direction: str) -> float | None:
    if direction == "down":
        return _safe_div(latest - price, latest) * 100 if latest else None
    return _safe_div(price - latest, latest) * 100 if latest else None


def _group_price_levels(
    candidates: tuple[tuple[str, float | None], ...],
    *,
    latest: float,
    ascending: bool,
    max_levels: int | None = None,
) -> tuple[tuple[float, tuple[str, ...]], ...]:
    grouped: dict[float, list[str]] = {}
    for label, price in candidates:
        if price is None or (price <= latest if ascending else price >= latest):
            continue
        grouped.setdefault(price, []).append(label)
    if not grouped:
        return ()
    prices = sorted(grouped, reverse=not ascending)
    if max_levels is not None:
        prices = prices[:max_levels]
    return tuple((price, tuple(grouped[price])) for price in prices)


def _pct_distance_from_current(current: float | int | None, reference: float | int | None) -> float | None:
    if current in (None, 0) or reference is None:
        return None
    return ((float(current) - float(reference)) / float(current)) * 100


def _format_headline_summary(result: TechnicalAnalysisResult) -> str:
    headline = _build_headline(result)
    if headline is None:
        return "短評：N/A"
    moving_average = result.snapshot.moving_average
    return "短評：" + build_technical_short_comment(
        rank=headline.rank,
        ma25_position_label=headline.ma25_position_label,
        collapse_state_label=headline.collapse_state_label,
        c2_fall_reason=headline.c2_fall_reason,
        ma5_slope=getattr(moving_average, "ma5_slope", None),
        ma5_slope_prev=getattr(moving_average, "ma5_slope_prev", None),
        ma5_slope_3d_ago=getattr(moving_average, "ma5_slope_3d_ago", None),
    )


def _format_position_assessment(result: TechnicalAnalysisResult) -> str:
    latest = _evaluation_price(result)
    ma25 = result.snapshot.moving_average.ma25
    assessment = _build_position_assessment(result)
    if latest is None or ma25 is None or assessment is None:
        return "崩れ警戒：N/A\nホールド判定：N/A"

    collapse_brief = build_collapse_score_brief(assessment.collapse_risk_score)
    collapse_reason = f"｜{assessment.collapse_risk_reason}" if assessment.collapse_risk_reason else ""
    lines = [
        f"崩れ {assessment.collapse_risk_score}/6：{collapse_brief.text}{collapse_reason}",
    ]
    if latest < ma25:
        established = "成立" if assessment.bottoming_start_established else "未成立"
        lines.append(f"底打ち初動判定：{established}")
    lines.append(f"ホールド判定：{assessment.hold_judgement}")
    return "\n".join(lines)


def _build_position_assessment(result: TechnicalAnalysisResult):
    snapshot = result.snapshot
    latest = _evaluation_price(result)
    vwap = _as_float(result.vwap_snapshot.get("vwap"))
    ma25 = snapshot.moving_average.ma25
    dev25_pct = _evaluation_dev25_pct(result)
    if latest is None or vwap is None or ma25 is None or dev25_pct is None:
        return None

    headline = _build_headline(result)
    if headline is None:
        return None
    return build_technical_position_assessment(
        latest=latest,
        vwap=vwap,
        ma25=ma25,
        ma5=getattr(snapshot.moving_average, "ma5", None),
        ma5_prev1=getattr(snapshot.moving_average, "ma5_prev1", None),
        ma5_slope=getattr(snapshot.moving_average, "ma5_slope", None),
        ma5_slope_prev=getattr(snapshot.moving_average, "ma5_slope_prev", None),
        ma5_slope_3d_ago=getattr(snapshot.moving_average, "ma5_slope_3d_ago", None),
        ma25_prev5=snapshot.moving_average.ma25_prev5,
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
    strategy_lines = _filter_strategy_lines_for_time(strategy_lines, result)
    return "\n".join(("戦略判定：", *strategy_lines))


def _filter_strategy_lines_for_time(
    strategy_lines: tuple[str, ...],
    result: TechnicalAnalysisResult,
) -> tuple[str, ...]:
    phase = _strategy_phase(result)
    if phase is None or strategy_lines == ("N/A（判定基準未設定）",):
        return strategy_lines

    deep = _line_starting_with(strategy_lines, "前場深押し")
    am_vwap = _line_starting_with(strategy_lines, "前場VWAP回復")
    pm_vwap = _line_starting_with(strategy_lines, "後場VWAP回復")

    if phase == "preopen":
        return tuple(
            line
            for line in (
                deep,
                am_vwap,
                _format_hold_limit_sell_line(result),
            )
            if line is not None
        )
    if phase == "am":
        return (am_vwap,) if am_vwap is not None else ()
    if phase == "lunch":
        return (pm_vwap,) if pm_vwap is not None else ()
    if phase == "pm":
        return (_replace_strategy_label(pm_vwap, "後場VWAP維持/利確/持ち越し判定"),) if pm_vwap is not None else ()
    if phase == "closing":
        return (_replace_strategy_label(pm_vwap, "持ち越し/利確"),) if pm_vwap is not None else ()
    return strategy_lines


def _line_starting_with(lines: tuple[str, ...], prefix: str) -> str | None:
    return next((line for line in lines if line.startswith(prefix)), None)


def _replace_strategy_label(line: str | None, label: str) -> str | None:
    if line is None:
        return None
    _, separator, body = line.partition("：")
    return line if not separator else f"{label}：{body}"


def _format_hold_limit_sell_line(result: TechnicalAnalysisResult) -> str:
    lines = _build_resistance_lines(result)
    target = _fmt_price_compact(lines[0].price) if lines else "N/A"
    return f"ホールド銘柄の指値売：抵抗線 {target}円 付近で部分利確・逆指値管理を確認。"


def _strategy_phase(result: TechnicalAnalysisResult) -> str | None:
    value = getattr(result, "evaluation_at", None)
    if isinstance(value, datetime):
        target = value.time()
    else:
        target = _time_from_timestamp_text(result.evaluation_price_timestamp)
    if target is None:
        return None
    if target < time(9, 0):
        return "preopen"
    if target < time(11, 30):
        return "am"
    if target < time(12, 30):
        return "lunch"
    if target < time(15, 0):
        return "pm"
    if target < time(15, 30):
        return "closing"
    return "closing"


def _time_from_timestamp_text(value: str | None) -> time | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M").time()
    except ValueError:
        return None


def _strategy_detail_code(result: TechnicalAnalysisResult, rank: str) -> str | None:
    if rank == "D1":
        return build_d1_detail(ma25_distance_atr=_evaluation_ma25_distance_atr(result))[0]
    if rank == "D3":
        sessions = result.three_session_momentum.sessions
        return build_d3_detail(
            volume_vs_avg20_pct=_ratio_pct(
                _evaluation_volume(result),
                result.snapshot.price.volume_avg20,
            ),
            high_breakout_count=_count_true(session.high_breakout for session in sessions),
            day_close_position=_range_position(
                _evaluation_price(result),
                _evaluation_low(result),
                _evaluation_high(result),
            ),
        )[0]
    if rank == "D2":
        sessions = result.three_session_momentum.sessions
        return build_d2_detail(
            latest=_evaluation_price(result) or 0.0,
            vwap=_as_float(result.vwap_snapshot.get("vwap")) or 0.0,
            day_open=_evaluation_open(result),
            day_high=_evaluation_high(result),
            day_low=_evaluation_low(result),
            day_close_position=_range_position(
                _evaluation_price(result),
                _evaluation_low(result),
                _evaluation_high(result),
            ),
            atr14=result.snapshot.range.atr14,
            volume_vs_avg20_pct=_ratio_pct(
                _evaluation_volume(result),
                result.snapshot.price.volume_avg20,
            ),
            rsi14=result.snapshot.rsi14,
            previous_low=result.snapshot.previous_session.prev_low,
            recent20_low=result.snapshot.breakline.recent20_low,
            ma75=result.snapshot.moving_average.ma75,
            recent60_low=result.snapshot.breakline.recent60_low,
            low_highers=tuple(session.low_higher for session in sessions),
        )[0]
    return None


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
    return "\n".join(
        [
            "■前日評価",
            f"前日終値：{_fmt_price_compact(prev_close)}円（VWAP{_fmt_price_signed_compact(prev_vwap_diff)}円／騰落率{_fmt_pct(previous.prev_change_pct)}）"
            f"　終端位置：{_fmt_position_pct(previous.prev_close_position)}　{_format_previous_candle(previous.candle_body_label, previous.wick_label)}"
            f"（レンジ{_fmt_price_compact(previous.prev_low)}－{_fmt_price_compact(previous.prev_high)}）",
            f"前日出来高：20日平均比　{_fmt_pct_unsigned(previous.prev_volume_vs_avg20_pct)}",
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
        ma25_distance_atr=_evaluation_ma25_distance_atr(result),
        ma5=getattr(snapshot.moving_average, "ma5", None),
        ma5_prev1=getattr(snapshot.moving_average, "ma5_prev1", None),
        ma5_slope=getattr(snapshot.moving_average, "ma5_slope", None),
        ma5_slope_prev=getattr(snapshot.moving_average, "ma5_slope_prev", None),
        ma5_slope_3d_ago=getattr(snapshot.moving_average, "ma5_slope_3d_ago", None),
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
        high_breakouts=tuple(session.high_breakout for session in sessions),
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


def _fmt_pct_ratio_no_decimal(change_pct: float | None) -> str:
    return "N/A" if change_pct is None else f"{100 + change_pct:.0f}%"


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
