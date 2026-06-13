"""Domain policy: technical summary ranks and nearby price lines."""

from __future__ import annotations

from app.domain.models.technical_summary import (
    TechnicalHeadlineSummary,
    TechnicalPositionAssessment,
    TechnicalSummaryLine,
    TechnicalSummaryRank,
)

RANK_LABELS: dict[TechnicalSummaryRank, str] = {
    "A1": "位置良好",
    "A2": "やや過熱",
    "B1": "上昇後半",
    "B2": "過熱極大",
    "C1": "押し目候補",
    "C2": "崩れ警戒",
    "D1": "戻り途中",
    "D2": "底打ち候補",
    "D3": "底打ち初動",
    "E": "下落トレンド",
}

RANK_ORDER: tuple[TechnicalSummaryRank, ...] = ("A1", "A2", "B1", "B2", "C1", "C2", "D1", "D2", "D3", "E")

HEADLINE_COMMENTS: dict[TechnicalSummaryRank, str] = {
    "A1": "順張り可。過熱なし。",
    "A2": "上昇継続中。ただし追いかけ注意。",
    "B1": "値幅は残るが、押しを待つ位置。",
    "B2": "新規買い非推奨。利確優先。",
    "C1": "支持線反発待ち。",
    "C2": "25日線割れ警戒。買いは待ち。",
    "D1": "25日線回復待ち。",
    "D2": "支持線確認中。買いは待ち。",
    "D3": "反転初動。25日線突破確認。",
    "E": "買い見送り。反転確認待ち。",
}

NEXT_ACTIONS: dict[TechnicalSummaryRank, str] = {
    "A1": "深押し、VWAP回復、後場VWAP維持は可。追加買いは条件付き可。",
    "A2": "支持線待ち。追加買いは小さく。",
    "B1": "新規は慎重。追加買い非推奨。",
    "B2": "短期監視のみ。追加買い不可。",
    "C1": "VWAP回復まで買い待ち。",
    "C2": "VWAP回復後も15分維持を確認。追加買い不可。",
    "D1": "後場VWAP維持なら監視継続。追加買いは25日線回復後。",
    "D2": "買い急がず。補助指標の確認待ち。",
    "D3": "深押し、VWAP回復は可。追加買いは25日線回復後。",
    "E": "監視のみ。新規買い不可。",
}

STRATEGY_LINES: dict[TechnicalSummaryRank, tuple[str, str, str] | None] = {
    "A1": (
        "前場深押し○：支持線付近 {support_range}円で検討。約定後はVWAP回復・維持を確認。",
        "前場VWAP回復◎：VWAP回復＋15分以上維持ならエントリー可。",
        "後場VWAP回復◎：後場VWAP上維持ならエントリー可。ホールド適性も高い。",
    ),
    "A2": (
        "前場深押し△：支持線付近 {support_range}円で小さく検討。追随買いは避ける。",
        "前場VWAP回復○：VWAP近辺まで押した後、再回復＋維持ならエントリー可。",
        "後場VWAP回復○：後場VWAP上維持ならエントリー可。ただし高値追いは避ける。",
    ),
    "B1": (
        "前場深押し△：支持線付近 {nearest_support}円でのみ小さく検討。VWAP未回復なら撤退。",
        "前場VWAP回復△：VWAP回復＋維持でも新規は慎重。高値追いは避ける。",
        "後場VWAP回復△：後場VWAP上維持なら短期限定で検討可。持ち越しは慎重。",
    ),
    "B2": (
        "前場深押し×：深押しに見えても崩れ初動の可能性が高い。",
        "前場VWAP回復×：VWAP回復だけでは新規不可。",
        "後場VWAP回復×：新規不可。保有中なら利確・逆指値管理を優先。",
    ),
    "C1": (
        "前場深押し×：VWAP下では深押し指値を避ける。支持線割れの中腹をつかみやすい。",
        "前場VWAP回復△：VWAP回復＋15分以上維持なら検討可。慎重なら後場まで待つ。",
        "後場VWAP回復○：後場VWAP回復＋上維持＋安値切り上げがあればエントリー可。",
    ),
    "C2": (
        "前場深押し×：25日線下では深押し指値を避ける。戻り売りの中腹をつかみやすい。",
        "前場VWAP回復×：VWAP回復だけでは根拠不足。25日線下ではだまし上げに注意。",
        "後場VWAP回復△：後場VWAP上維持＋安値切り上げなら小さく検討可。慎重なら25日線回復を待つ。",
    ),
    "D1": None,
    "D2": None,
    "D3": None,
    "E": (
        "前場深押し×：下降トレンド中の深押しは避ける。",
        "前場VWAP回復×：前場VWAP回復だけでは新規不可。だまし上げ警戒。",
        "後場VWAP回復△：後場VWAP回復＋上維持＋安値切り上げ＋出来高増加が揃えば小さく検討可。原則は25日線回復待ち。",
    ),
}

FOCUS_THEME_KEYWORDS = ("半導体", "電線", "AI", "ＡＩ")


def is_focus_theme(name: str) -> bool:
    normalized = name.upper()
    return any(keyword.upper() in normalized for keyword in FOCUS_THEME_KEYWORDS)


def build_technical_strategy_lines(
    rank: TechnicalSummaryRank,
    *,
    support_range: str = "N/A",
    nearest_support: str = "N/A",
) -> tuple[str, ...]:
    templates = STRATEGY_LINES[rank]
    if templates is None:
        return ("N/A（判定基準未設定）",)
    return tuple(
        template.format(support_range=support_range, nearest_support=nearest_support)
        for template in templates
    )


def classify_technical_summary_rank(
    *,
    dev25_pct: float,
    latest: float,
    vwap: float,
    focus_theme: bool,
    ma25_distance_atr: float | None = None,
    ma25: float | None = None,
    ma25_prev5: float | None = None,
    rsi14: float | None = None,
    three_session_change_pct: float | None = None,
    high_breakout_count: int | None = None,
    low_higher_count: int | None = None,
    day_close_position: float | None = None,
    day_open: float | None = None,
    day_high: float | None = None,
    day_low: float | None = None,
    atr14: float | None = None,
    volume_vs_avg20_pct: float | None = None,
    recent60_range_position: float | None = None,
    previous_low: float | None = None,
    recent20_low: float | None = None,
    ma75: float | None = None,
    recent60_low: float | None = None,
) -> TechnicalSummaryRank:
    del focus_theme
    vwap_up = latest > vwap
    ma25_slope = _ma25_slope(ma25, ma25_prev5)
    range_position_pct = _position_pct(recent60_range_position)
    close_position_pct = _position_pct(day_close_position)

    if dev25_pct >= 10 or _gte(ma25_distance_atr, 2.0):
        if _gte(rsi14, 70) or _gte(three_session_change_pct, 10) or _gte(volume_vs_avg20_pct, 150):
            return "B2"
        return "B2"

    if dev25_pct >= 0:
        if dev25_pct >= 7 and (_gte(three_session_change_pct, 6) or _gte(range_position_pct, 80) or vwap_up):
            return "B1"
        if vwap_up and dev25_pct >= 4:
            return "A2"
        if vwap_up:
            return "A1"
        if dev25_pct <= 3 and (ma25_slope in {"flat", "down"} or low_higher_count == 0):
            return "C2"
        return "C1"

    if vwap_up:
        if (
            _gte(low_higher_count, 2)
            and _gte(high_breakout_count, 1)
            and _gte(close_position_pct, 60)
            and dev25_pct >= -8
        ):
            return "D3"
        return "D1"

    d2_evaluation = _evaluate_d2_bottoming_candidate(
        latest=latest,
        vwap=vwap,
        day_open=day_open,
        day_high=day_high,
        day_low=day_low,
        day_close_position=day_close_position,
        atr14=atr14,
        volume_vs_avg20_pct=volume_vs_avg20_pct,
        rsi14=rsi14,
        low_higher_count=low_higher_count,
        previous_low=previous_low,
        recent20_low=recent20_low,
        ma75=ma75,
        recent60_low=recent60_low,
    )
    if d2_evaluation == "exclude":
        return "E"
    if dev25_pct >= -12 and d2_evaluation in {"strong", "weak"}:
        return "D2"
    return "E"


def build_technical_headline_summary(
    *,
    dev25_pct: float,
    latest: float,
    vwap: float,
    focus_theme: bool = False,
    ma25_distance_atr: float | None = None,
    ma25: float | None = None,
    ma25_prev5: float | None = None,
    rsi14: float | None = None,
    three_session_change_pct: float | None = None,
    high_breakout_count: int | None = None,
    low_higher_count: int | None = None,
    day_close_position: float | None = None,
    day_open: float | None = None,
    day_high: float | None = None,
    day_low: float | None = None,
    atr14: float | None = None,
    volume_vs_avg20_pct: float | None = None,
    recent60_range_position: float | None = None,
    previous_low: float | None = None,
    recent20_low: float | None = None,
    ma75: float | None = None,
    recent60_low: float | None = None,
) -> TechnicalHeadlineSummary:
    rank = classify_technical_summary_rank(
        dev25_pct=dev25_pct,
        latest=latest,
        vwap=vwap,
        focus_theme=focus_theme,
        ma25_distance_atr=ma25_distance_atr,
        ma25=ma25,
        ma25_prev5=ma25_prev5,
        rsi14=rsi14,
        three_session_change_pct=three_session_change_pct,
        high_breakout_count=high_breakout_count,
        low_higher_count=low_higher_count,
        day_close_position=day_close_position,
        day_open=day_open,
        day_high=day_high,
        day_low=day_low,
        atr14=atr14,
        volume_vs_avg20_pct=volume_vs_avg20_pct,
        recent60_range_position=recent60_range_position,
        previous_low=previous_low,
        recent20_low=recent20_low,
        ma75=ma75,
        recent60_low=recent60_low,
    )
    comment = HEADLINE_COMMENTS[rank]
    next_action = NEXT_ACTIONS[rank]
    if rank == "D2":
        d2_evaluation = _evaluate_d2_bottoming_candidate(
            latest=latest,
            vwap=vwap,
            day_open=day_open,
            day_high=day_high,
            day_low=day_low,
            day_close_position=day_close_position,
            atr14=atr14,
            volume_vs_avg20_pct=volume_vs_avg20_pct,
            rsi14=rsi14,
            low_higher_count=low_higher_count,
            previous_low=previous_low,
            recent20_low=recent20_low,
            ma75=ma75,
            recent60_low=recent60_low,
        )
        if d2_evaluation == "strong":
            comment = "底打ち候補強。"
            next_action = "VWAP回復待ち(補助指標2つ以上)。"
        else:
            comment = "底打ち候補。"
            next_action = "買い急がず(補助指標1つ以下)。"
    return TechnicalHeadlineSummary(
        rank=rank,
        rank_label=RANK_LABELS[rank],
        comment=comment,
        next_action=next_action,
    )


def build_technical_position_assessment(
    *,
    latest: float,
    vwap: float,
    ma25: float,
    atr14: float | None,
    day_open: float | None,
    day_high: float | None,
    day_low: float | None,
    day_close_position: float | None,
    volume_vs_avg20_pct: float | None,
    high_breakouts: tuple[bool | None, ...],
    low_highers: tuple[bool | None, ...],
    previous_low: float | None,
    recent20_low: float | None,
    ma75: float | None,
    recent60_low: float | None,
    headline_rank: TechnicalSummaryRank,
) -> TechnicalPositionAssessment:
    """Score collapse risk and derive the single-stock hold judgement."""
    all_high_breakouts_failed = _all_false(high_breakouts)
    all_low_highers_failed = _all_false(low_highers)
    support_distance_atr = _nearest_support_distance_atr(
        latest=latest,
        atr14=atr14,
        supports=(ma25, previous_low, recent20_low, ma75, recent60_low),
    )
    support_is_far = support_distance_atr is not None and support_distance_atr > 0.7
    support_is_near = support_distance_atr is not None and support_distance_atr <= 0.7
    bearish_or_stalling = _is_significant_bearish(
        latest=latest,
        day_open=day_open,
        atr14=atr14,
    ) or _is_upper_price_stalling(
        latest=latest,
        day_open=day_open,
        day_high=day_high,
        day_low=day_low,
    )

    score = sum(
        (
            latest < ma25,
            latest < vwap,
            all_low_highers_failed,
            all_high_breakouts_failed,
            day_close_position is not None and day_close_position < 0.4,
            volume_vs_avg20_pct is not None and volume_vs_avg20_pct > 100 and bearish_or_stalling,
            support_is_far,
        )
    )
    level = "低" if score <= 1 else "中" if score <= 3 else "高"

    ma25_up = latest >= ma25
    vwap_up = latest >= vwap
    ma25_near = atr14 not in (None, 0) and abs(latest - ma25) / atr14 <= 0.7
    any_low_higher = any(value is True for value in low_highers)
    close_is_low = day_close_position is not None and day_close_position < 0.5
    volume_is_low = volume_vs_avg20_pct is not None and volume_vs_avg20_pct < 80

    if not vwap_up and not ma25_up and all_low_highers_failed and support_is_far:
        hold = "×"
    elif (vwap_up and not ma25_up) or close_is_low or volume_is_low:
        hold = "△"
    elif ma25_up and vwap_up and _gte(_position_pct(day_close_position), 50) and _gte(volume_vs_avg20_pct, 80) and support_is_near:
        hold = "◎"
    elif (ma25_up or ma25_near) and vwap_up and any_low_higher:
        hold = "○"
    else:
        hold = "△"

    return TechnicalPositionAssessment(
        collapse_risk_score=score,
        collapse_risk_level=level,
        hold_judgement=hold,
        bottoming_start_established=latest < ma25 and headline_rank == "D3",
    )


def build_nearby_support_lines(
    *,
    latest: float,
    ma25: float | None,
    previous_low: float | None,
    recent20_low: float | None,
    ma75: float | None,
    recent60_low: float | None,
) -> tuple[TechnicalSummaryLine, ...]:
    return _dedupe_lines(
        _lines_below(
            latest,
            (
                TechnicalSummaryLine("25ME", ma25) if ma25 is not None else None,
                TechnicalSummaryLine("PrevL", previous_low) if previous_low is not None else None,
                TechnicalSummaryLine("20D-L", recent20_low) if recent20_low is not None else None,
                TechnicalSummaryLine("75ME", ma75) if ma75 is not None else None,
                TechnicalSummaryLine("60D-L", recent60_low) if recent60_low is not None else None,
            ),
        )
    )[:2]


def build_nearby_resistance_lines(
    *,
    latest: float,
    previous_high: float | None,
    recent20_high: float | None,
    recent60_high: float | None,
    ma25: float | None,
) -> tuple[TechnicalSummaryLine, ...]:
    return _dedupe_lines(
        _lines_above(
            latest,
            (
                TechnicalSummaryLine("PrevH", previous_high) if previous_high is not None else None,
                TechnicalSummaryLine("20D-H", recent20_high) if recent20_high is not None else None,
                TechnicalSummaryLine("60D-H", recent60_high) if recent60_high is not None else None,
                TechnicalSummaryLine("25ME", ma25) if ma25 is not None else None,
            ),
        )
    )[:2]


def _lines_below(
    latest: float,
    lines: tuple[TechnicalSummaryLine | None, ...],
) -> tuple[TechnicalSummaryLine, ...]:
    candidates = [line for line in lines if line is not None and line.price < latest]
    return tuple(sorted(candidates, key=lambda line: line.price, reverse=True))


def _lines_above(
    latest: float,
    lines: tuple[TechnicalSummaryLine | None, ...],
) -> tuple[TechnicalSummaryLine, ...]:
    candidates = [line for line in lines if line is not None and line.price > latest]
    return tuple(sorted(candidates, key=lambda line: line.price))


def _dedupe_lines(lines: tuple[TechnicalSummaryLine, ...]) -> tuple[TechnicalSummaryLine, ...]:
    seen: set[float] = set()
    result: list[TechnicalSummaryLine] = []
    for line in lines:
        if line.price in seen:
            continue
        seen.add(line.price)
        result.append(line)
    return tuple(result)


def _ma25_slope(ma25: float | None, ma25_prev5: float | None) -> str:
    if ma25 is None or ma25_prev5 is None:
        return "unknown"
    if ma25 > ma25_prev5:
        return "up"
    if ma25 < ma25_prev5:
        return "down"
    return "flat"


def _position_pct(value: float | None) -> float | None:
    return None if value is None else value * 100


def _gte(value: float | int | None, threshold: float | int) -> bool:
    return value is not None and value >= threshold


def _evaluate_d2_bottoming_candidate(
    *,
    latest: float,
    vwap: float,
    day_open: float | None,
    day_high: float | None,
    day_low: float | None,
    day_close_position: float | None,
    atr14: float | None,
    volume_vs_avg20_pct: float | None,
    rsi14: float | None,
    low_higher_count: int | None,
    previous_low: float | None,
    recent20_low: float | None,
    ma75: float | None,
    recent60_low: float | None,
) -> str:
    if atr14 in (None, 0) or day_low is None or day_high is None or day_open is None:
        return "none"
    support = _nearest_d2_support(
        day_low=day_low,
        atr14=atr14,
        supports=(previous_low, recent20_low, ma75, recent60_low),
    )
    if support is None:
        return "none"
    close_position_pct = _position_pct(day_close_position)
    if not _gte(close_position_pct, 40):
        return "none"
    if latest <= support:
        return "none"
    if latest < vwap - atr14 or latest > vwap:
        return "exclude" if latest < vwap - atr14 else "none"
    if _is_volume_surge_big_bearish(
        day_open=day_open,
        day_high=day_high,
        day_low=day_low,
        latest=latest,
        volume_vs_avg20_pct=volume_vs_avg20_pct,
    ):
        return "exclude"
    if low_higher_count == 0 and close_position_pct <= 50:
        return "exclude"

    score = _d2_auxiliary_score(
        latest=latest,
        day_open=day_open,
        day_high=day_high,
        day_low=day_low,
        support=support,
        volume_vs_avg20_pct=volume_vs_avg20_pct,
        rsi14=rsi14,
    )
    return "strong" if score >= 2 else "weak"


def _nearest_d2_support(
    *,
    day_low: float,
    atr14: float,
    supports: tuple[float | None, ...],
) -> float | None:
    candidates = [
        support
        for support in supports
        if support is not None and abs(day_low - support) <= 0.35 * atr14
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda support: abs(day_low - support))


def _d2_auxiliary_score(
    *,
    latest: float,
    day_open: float,
    day_high: float,
    day_low: float,
    support: float,
    volume_vs_avg20_pct: float | None,
    rsi14: float | None,
) -> int:
    score = 0
    if _gte(volume_vs_avg20_pct, 80):
        score += 1
    if _lower_wick_ratio(day_open=day_open, day_high=day_high, day_low=day_low, latest=latest) > 0.2:
        score += 1
    if rsi14 is not None and 30 <= rsi14 <= 45:
        score += 1
    if day_low < support:
        score -= 1
    return score


def _is_volume_surge_big_bearish(
    *,
    day_open: float,
    day_high: float,
    day_low: float,
    latest: float,
    volume_vs_avg20_pct: float | None,
) -> bool:
    day_range = day_high - day_low
    if day_range <= 0:
        return False
    body_ratio = abs(latest - day_open) / day_range
    return _gte(volume_vs_avg20_pct, 180) and latest < day_open and body_ratio >= 0.65


def _lower_wick_ratio(*, day_open: float, day_high: float, day_low: float, latest: float) -> float:
    day_range = day_high - day_low
    if day_range <= 0:
        return 0.0
    return max(0.0, min(day_open, latest) - day_low) / day_range


def _all_false(values: tuple[bool | None, ...]) -> bool:
    return bool(values) and all(value is False for value in values)


def _nearest_support_distance_atr(
    *,
    latest: float,
    atr14: float | None,
    supports: tuple[float | None, ...],
) -> float | None:
    if atr14 in (None, 0):
        return None
    candidates = [support for support in supports if support is not None and support < latest]
    if not candidates:
        return None
    nearest = max(candidates)
    return (latest - nearest) / atr14


def _is_significant_bearish(*, latest: float, day_open: float | None, atr14: float | None) -> bool:
    return (
        day_open is not None
        and atr14 not in (None, 0)
        and latest < day_open
        and abs(latest - day_open) >= 0.15 * atr14
    )


def _is_upper_price_stalling(
    *,
    latest: float,
    day_open: float | None,
    day_high: float | None,
    day_low: float | None,
) -> bool:
    if day_open is None or day_high is None or day_low is None:
        return False
    day_range = day_high - day_low
    if day_range <= 0:
        return False
    body = abs(latest - day_open)
    upper_wick = day_high - max(day_open, latest)
    return upper_wick / day_range >= 0.45 and upper_wick >= body * 1.5


__all__ = [
    "RANK_LABELS",
    "RANK_ORDER",
    "build_technical_headline_summary",
    "build_technical_position_assessment",
    "build_technical_strategy_lines",
    "build_nearby_resistance_lines",
    "build_nearby_support_lines",
    "classify_technical_summary_rank",
    "is_focus_theme",
]
