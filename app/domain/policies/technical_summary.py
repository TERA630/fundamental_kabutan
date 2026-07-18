"""Domain policy: technical summary ranks and nearby price lines."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.domain.models.signal_atom import SignalAtom, score_signal_atoms
from app.domain.models.technical_summary import (
    CollapseStateCode,
    Ma25PositionBandCode,
    ReversalStateCode,
    TechnicalHeadlineSummary,
    TechnicalPositionAssessment,
    TechnicalSummaryLine,
    TechnicalSummaryRank,
)
from app.domain.policies.range_table import RangeBand, RangeTable

RANK_LABELS: dict[TechnicalSummaryRank, str] = {
    "B2": "極端過熱",
    "B1": "過熱後半",
    "A2": "過熱選別",
    "A1": "位置良好",
    "A1弱": "上方乖離",
    "C1": "奪回待ち",
    "D1": "反転初動候補・検証不足",
    "E": "25日線下",
}

RANK_ORDER: tuple[TechnicalSummaryRank, ...] = (
    "A1",
    "A1弱",
    "A2",
    "C1",
    "D1",
    "B1",
    "B2",
    "E",
)

HEADLINE_COMMENTS: dict[TechnicalSummaryRank, str] = {
    "B2": "新規買い非推奨。利確優先。",
    "B1": "上昇余地はあるが逆行リスクも高い。",
    "A2": "高モメンタム。上昇継続を確認。",
    "A1": "順張り候補。位置良好。",
    "A1弱": "中期上昇余地はあるが、短期下振れに注意。",
    "C1": "方向未確定。",
    "D1": "25日線奪回待ち。上値確認中。",
    "E": "買い見送り。反転確認待ち。",
}

SINGLE_STOCK_POSITION_DESCRIPTIONS: dict[TechnicalSummaryRank, str] = {
    "B2": "上値余地より、逆行リスクが高い位置",
    "B1": "高収益を狙えるが、逆行リスクも高い。",
    "A2": "高モメンタム。上昇継続候補。",
    "A1": "安定上昇または中期モメンタムの買い候補",
    "A1弱": "中期上昇余地はあるが、初期逆行に注意。",
    "C1": "方向未確定",
    "D1": HEADLINE_COMMENTS["D1"],
    "E": HEADLINE_COMMENTS["E"],
}

@dataclass(frozen=True)
class Ma25PositionBand:
    code: Ma25PositionBandCode
    rank: TechnicalSummaryRank
    label: str
    comment: str
    recommendation: str
    effect: Literal["positive", "negative", "neutral", "unavailable"]


_MA25_POSITION_BAND_TABLE = RangeTable[Ma25PositionBand](
    bands=(
        RangeBand(
            12,
            Ma25PositionBand(
                "extreme", "B2", "極端過熱", "極端過熱", "新規買い見送り・利確優先", "negative"
            ),
        ),
        RangeBand(
            10,
            Ma25PositionBand(
                "late_overheat", "B1", "過熱後半", "過熱後半", "過熱後半｜新規買い見送り", "negative"
            ),
        ),
        RangeBand(
            8,
            Ma25PositionBand(
                "overheat_selection", "A2", "過熱選別", "過熱帯", "過熱帯｜追いかけ禁止", "negative"
            ),
        ),
        RangeBand(
            4,
            Ma25PositionBand(
                "upper_deviation", "A1弱", "上方乖離", "中央値マイナス", "中央値マイナス｜押し目確認", "neutral"
            ),
        ),
        RangeBand(
            0,
            Ma25PositionBand(
                "good_position", "A1", "位置良好", "位置良好", "位置良好｜エントリー優先帯", "positive"
            ),
        ),
        RangeBand(
            -2,
            Ma25PositionBand(
                "reclaim_wait", "C1", "奪回待ち", "25日線直下", "25日線奪回確認まで見送り", "neutral"
            ),
        ),
        RangeBand(
            -4,
            Ma25PositionBand(
                "reversal_candidate",
                "D1",
                "反転初動候補・検証不足",
                "件数不足",
                "件数不足｜25日線奪回待ち",
                "unavailable",
            ),
        ),
    ),
    default=Ma25PositionBand("below", "E", "25日線下", "反転未確認", "反転確認まで見送り", "neutral"),
)


def classify_ma25_position_band(dev25_pct: float) -> Ma25PositionBand:
    return _MA25_POSITION_BAND_TABLE.resolve(dev25_pct)


@dataclass(frozen=True)
class BacktestEntryGuidance:
    """One-year backtest guidance, separate from the technical state rank."""

    position_label: str
    observation: str
    recommendation: str
    effect: Literal["positive", "negative", "neutral", "unavailable"]


def classify_backtest_entry_guidance(dev25_pct: float) -> BacktestEntryGuidance:
    """Classify entry guidance from the latest one-year backtest bands."""

    band = classify_ma25_position_band(dev25_pct)
    return BacktestEntryGuidance(
        position_label=band.label,
        observation=band.comment,
        recommendation=band.recommendation,
        effect=band.effect,
    )

D_DETAIL_MAIN_JUDGEMENTS: dict[str, str] = {
    "D1a": "25日線奪回待ち。D3化は反転観測",
    "D1b": "25日線奪回待ち。新規は原則不可",
    "D1": "判定保留。新規不可",
    "D2": "支持線反発を観測。25日線奪回待ち",
    "D2弱": "支持線根拠が弱い。25日線奪回待ち",
    "D3強": "反転観測強。25日線奪回待ち",
    "D3": "反転観測。25日線奪回待ち",
    "D3弱": "反転観測弱。25日線奪回待ち",
}


@dataclass(frozen=True)
class CollapseStateAssessment:
    score: int
    code: CollapseStateCode
    label: str
    is_alert: bool
    reason: str | None


@dataclass(frozen=True)
class ReversalStateAssessment:
    code: ReversalStateCode
    label: str | None
    legacy_detail_rank: str | None = None


@dataclass(frozen=True)
class CollapseScoreBrief:
    label: str
    comment: str

    @property
    def text(self) -> str:
        return f"{self.label}｜{self.comment}"


_COLLAPSE_SCORE_BRIEF_TABLE = RangeTable[CollapseScoreBrief](
    bands=(
        RangeBand(5, CollapseScoreBrief("ほぼ触らない", "構造回復まで見送り")),
        RangeBand(4, CollapseScoreBrief("原則回避", "新規買い回避")),
        RangeBand(2, CollapseScoreBrief("条件付き候補", "後場VWAP上維持・価格構造回復を確認")),
    ),
    default=CollapseScoreBrief("候補", "買い条件は別確認"),
)


@dataclass(frozen=True)
class _CollapseRiskSignals:
    atoms: tuple[SignalAtom, ...]

    def __post_init__(self) -> None:
        signal_ids = tuple(atom.signal_id for atom in self.atoms)
        if len(signal_ids) != len(set(signal_ids)):
            raise ValueError("Collapse risk signal IDs must be unique")

    def _matched(self, signal_id: str) -> bool:
        return next(atom.matched for atom in self.atoms if atom.signal_id == signal_id)

    @property
    def score(self) -> int:
        return score_signal_atoms(self.atoms)

    @property
    def vwap_break(self) -> bool:
        return self._matched("vwap_break")

    @property
    def vwap_clear_break(self) -> bool:
        return self._matched("vwap_clear_break")

    @property
    def low_higher_failed(self) -> bool:
        return self._matched("low_higher_failed")

    @property
    def high_breakout_failed(self) -> bool:
        return self._matched("high_breakout_failed")

    @property
    def close_position_low(self) -> bool:
        return self._matched("close_position_low")

    @property
    def volume_bearish_or_stalling(self) -> bool:
        return self._matched("volume_bearish_or_stalling")

    @property
    def support_far(self) -> bool:
        return self._matched("support_far")

    @property
    def ma25_slope_bad(self) -> bool:
        return self._matched("ma25_slope_bad")

    @property
    def ma5_down(self) -> bool:
        return self._matched("ma5_down")

    @property
    def price_structure_bad(self) -> bool:
        return self.vwap_break or self.low_higher_failed or self.close_position_low

    @property
    def collapse_risk_reason(self) -> str | None:
        """Return the first major collapse reason in display priority order."""

        if self.vwap_clear_break and self.close_position_low:
            return "即時崩れ：VWAP明確割れ＋終端位置低下"
        if self.vwap_clear_break and self.low_higher_failed:
            return "即時崩れ：VWAP明確割れ＋安値切り上げ失敗"
        if self.volume_bearish_or_stalling and self.close_position_low:
            return "即時崩れ：出来高陰線/上値失速＋終端位置低下"
        if self.support_far and self.vwap_break:
            return "即時崩れ：支持線崩落"
        if self.ma5_down and self.ma25_slope_bad:
            return "下行初動：5日線下向き＋25日線下向き"
        if self.ma5_down and self.vwap_break:
            return "下行初動：5日線下向き＋VWAP割れ"
        if self.ma25_slope_bad and self.score >= 2 and self.price_structure_bad:
            return "構造崩れ：25日線下向き＋崩れスコア中以上＋価格構造悪化"
        if self.score >= 4:
            return "高リスク：崩れスコア高リスク"
        return None


UPPER_STALL_WICK_RATIO = 0.45

STRATEGY_LINES: dict[TechnicalSummaryRank, tuple[str, str] | None] = {
    "A1": (
        "前場VWAP回復◎：VWAP回復＋15分以上維持ならエントリー可。",
        "後場VWAP回復◎：後場VWAP上維持ならエントリー可。ホールド適性も高い。",
    ),
    "A2": (
        "前場VWAP回復○：VWAP近辺まで押した後、再回復＋維持ならエントリー可。",
        "後場VWAP回復○：後場VWAP上維持ならエントリー可。ただし高値追いは避ける。",
    ),
    "A1弱": (
        "前場VWAP回復○：VWAP回復＋15分以上維持なら小さく検討可。",
        "後場VWAP回復○：後場VWAP上維持ならエントリー候補。支持線割れは見送り。",
    ),
    "B1": (
        "前場VWAP回復△：VWAP回復＋維持でも新規は慎重。高値追いは避ける。",
        "後場VWAP回復△：後場VWAP上維持なら短期限定で検討可。持ち越しは慎重。",
    ),
    "B2": (
        "前場VWAP回復×：VWAP回復だけでは新規不可。",
        "後場VWAP回復×：新規不可。保有中なら利確・逆指値管理を優先。",
    ),
    "C1": (
        "前場VWAP回復△：VWAP回復＋15分以上維持なら検討可。慎重なら後場まで待つ。",
        "後場VWAP回復○：後場VWAP回復＋上維持＋安値切り上げがあればエントリー可。",
    ),
    "D1": None,
    "E": (
        "前場VWAP回復×：前場VWAP回復だけでは新規不可。だまし上げ警戒。",
        "後場VWAP回復△：後場VWAP回復＋上維持＋安値切り上げ＋出来高増加が揃えば小さく検討可。原則は25日線回復待ち。",
    ),
}

COLLAPSE_STRATEGY_LINES = (
    "前場VWAP回復×：VWAP回復だけでは根拠不足。安値切り上げと高値更新を確認する。",
    "後場VWAP回復△：後場VWAP上維持＋安値切り上げなら小さく検討可。慎重なら崩れ条件の解消を待つ。",
)

def build_technical_strategy_lines(
    rank: TechnicalSummaryRank,
    *,
    reversal_state_code: ReversalStateCode = "not_applicable",
    collapse_alert: bool = False,
    detail_code: str | None = None,
    vwap_recovery_range: str = "N/A",
) -> tuple[str, ...]:
    if collapse_alert:
        return COLLAPSE_STRATEGY_LINES
    if reversal_state_code == "vwap_recovered_unconfirmed" or (
        rank == "D1" and reversal_state_code == "not_applicable"
    ):
        return _build_d1_strategy_lines(
            detail_code=detail_code or "D1",
        )
    if reversal_state_code == "support_bounce_candidate":
        prefix = "D2弱｜支持線根拠弱い｜" if detail_code == "D2弱" else ""
        return (
            f"前場VWAP回復△：VWAP回復帯 {vwap_recovery_range} と反転状態を確認するが、新規は25日線奪回待ち。",
            f"後場VWAP回復△：{prefix}後場VWAP上維持でも反転観測に留め、持ち越し判断は25日線奪回後。",
        )
    if reversal_state_code == "reversal_confirmed":
        return _build_d3_strategy_lines(
            detail_code=detail_code or "D3",
            vwap_recovery_range=vwap_recovery_range,
        )
    strategy_rank = "E" if reversal_state_code == "reversal_unconfirmed" else rank
    templates = STRATEGY_LINES[strategy_rank]
    if templates is None:
        return ("N/A（判定基準未設定）",)
    return templates


def build_d_detail_headline(
    rank: str,
    *,
    ma25_distance_atr: float | None = None,
    volume_vs_avg20_pct: float | None = None,
    high_breakout_count: int | None = None,
    day_close_position: float | None = None,
    d2_detail_code: str | None = None,
    dev25_pct: float | None = None,
) -> str | None:
    if rank == "D1":
        code, label = build_d1_detail(ma25_distance_atr=ma25_distance_atr)
        return f"{code} {label}｜{D_DETAIL_MAIN_JUDGEMENTS[code]}"
    if rank == "D2":
        code = "D2弱" if d2_detail_code == "D2弱" else "D2"
        label = "底打ち候補・弱" if code == "D2弱" else "底打ち候補"
        state = "支持線根拠弱い" if code == "D2弱" else "支持線反発待ち"
        text = f"{code} {label}｜{state}｜{D_DETAIL_MAIN_JUDGEMENTS[code]}"
        return _append_dev25_risk_label(text, rank=rank, dev25_pct=dev25_pct)
    if rank == "D3":
        code, label = build_d3_detail(
            volume_vs_avg20_pct=volume_vs_avg20_pct,
            high_breakout_count=high_breakout_count,
            day_close_position=day_close_position,
        )
        text = f"{code}｜{label}｜{D_DETAIL_MAIN_JUDGEMENTS[code]}"
        return _append_dev25_risk_label(text, rank=rank, dev25_pct=dev25_pct)
    return None


def _append_dev25_risk_label(
    text: str,
    *,
    rank: TechnicalSummaryRank,
    dev25_pct: float | None,
) -> str:
    if dev25_pct is None:
        return text
    risk_label = build_dev25_risk_label(rank, dev25_pct)
    return text if risk_label is None else f"{text}｜{risk_label}"


def _build_d1_strategy_lines(
    *,
    detail_code: str,
) -> tuple[str, ...]:
    if detail_code == "D1a":
        return (
            "前場VWAP回復△：VWAP回復とD3化は反転観測に留め、新規は25日線奪回待ち。",
            "後場VWAP回復△：後場VWAP上維持でも新規は見送り、25日線奪回を確認。",
        )
    if detail_code == "D1b":
        return (
            "前場VWAP回復△：VWAP上でも反転確認中。新規は25日線奪回待ち。",
            "後場VWAP回復△：回復しても持ち越し判断は25日線奪回後。",
        )
    return (
        "前場VWAP回復△：D3条件を満たしても反転観測に留め、25日線奪回待ち。",
        "後場VWAP回復△：判定材料不足。新規は見送り。",
    )


def _build_d3_strategy_lines(
    *,
    detail_code: str,
    vwap_recovery_range: str,
) -> tuple[str, ...]:
    if detail_code == "D3強":
        return (
            "前場VWAP回復○：反転観測強。VWAP15分維持と出来高を確認し、新規は25日線奪回待ち。",
            "後場VWAP回復○：後場VWAP上維持でも、持ち越し判断は25日線奪回後。",
        )
    if detail_code == "D3弱":
        return (
            "前場VWAP回復△：反転形はあるが弱い。25日線奪回まで監視継続。",
            "後場VWAP回復△：後場VWAP維持でも反転観測に留める。",
        )
    return (
        f"前場VWAP回復○：反転観測。VWAP回復帯 {vwap_recovery_range} を維持しても新規は25日線奪回待ち。",
        "後場VWAP回復○：後場VWAP上維持は観測継続条件。持ち越し判断は25日線奪回後。",
    )


def classify_position_rank(dev25_pct: float) -> TechnicalSummaryRank:
    """Classify the primary rank solely from the one-year MA25 position band."""

    return classify_ma25_position_band(dev25_pct).rank


def classify_technical_summary_rank(*, dev25_pct: float, **_: object) -> TechnicalSummaryRank:
    """Compatibility wrapper for callers migrating to ``classify_position_rank``."""

    return classify_position_rank(dev25_pct)


def evaluate_reversal_state(
    *,
    dev25_pct: float,
    latest: float,
    vwap: float,
    high_breakout_count: int | None = None,
    low_higher_count: int | None = None,
    day_close_position: float | None = None,
    day_open: float | None = None,
    day_high: float | None = None,
    day_low: float | None = None,
    atr14: float | None = None,
    volume_vs_avg20_pct: float | None = None,
    rsi14: float | None = None,
    previous_low: float | None = None,
    recent20_low: float | None = None,
    ma75: float | None = None,
    recent60_low: float | None = None,
    vwap_maintained_15m: bool | None = None,
    low_highers: tuple[bool | None, ...] = (),
) -> ReversalStateAssessment:
    """Evaluate below-MA25 price action without changing the primary position rank."""

    if dev25_pct >= 0:
        return ReversalStateAssessment("not_applicable", None)

    if latest > vwap:
        if (
            _gte(low_higher_count, 2)
            and _gte(_position_pct(day_close_position), 60)
            and vwap_maintained_15m is True
        ):
            return ReversalStateAssessment("reversal_confirmed", "反転確認", "D3")
        return ReversalStateAssessment(
            "vwap_recovered_unconfirmed",
            "VWAP回復・確認不足",
            "D1",
        )

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
        previous_low=previous_low,
        recent20_low=recent20_low,
        ma75=ma75,
        recent60_low=recent60_low,
        low_highers=low_highers,
    )
    if d2_evaluation in {"strong", "weak"}:
        return ReversalStateAssessment(
            "support_bounce_candidate",
            "支持線反発候補",
            "D2弱" if d2_evaluation == "weak" else "D2",
        )
    return ReversalStateAssessment("reversal_unconfirmed", "反転未確認", "E")


def build_technical_headline_summary(
    *,
    dev25_pct: float,
    latest: float,
    vwap: float,
    ma25_distance_atr: float | None = None,
    ma5: float | None = None,
    ma5_prev1: float | None = None,
    ma5_slope: float | None = None,
    ma5_slope_prev: float | None = None,
    ma5_slope_3d_ago: float | None = None,
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
    vwap_maintained_15m: bool | None = None,
    low_highers: tuple[bool | None, ...] = (),
    high_breakouts: tuple[bool | None, ...] = (),
) -> TechnicalHeadlineSummary:
    rank = classify_position_rank(dev25_pct)
    reversal_state = evaluate_reversal_state(
        dev25_pct=dev25_pct,
        latest=latest,
        vwap=vwap,
        rsi14=rsi14,
        low_higher_count=low_higher_count,
        day_close_position=day_close_position,
        day_open=day_open,
        day_high=day_high,
        day_low=day_low,
        atr14=atr14,
        volume_vs_avg20_pct=volume_vs_avg20_pct,
        previous_low=previous_low,
        recent20_low=recent20_low,
        ma75=ma75,
        recent60_low=recent60_low,
        vwap_maintained_15m=vwap_maintained_15m,
        low_highers=low_highers,
    )
    guidance = classify_backtest_entry_guidance(dev25_pct)
    overheated = _has_b1_overheat_condition(
        three_session_change_pct=three_session_change_pct,
        recent60_range_position=recent60_range_position,
        rsi14=rsi14,
    )
    position_label = guidance.position_label
    if 8 <= dev25_pct < 10 and overheated:
        position_label += "（他指標過熱）"
    rank_label = position_label
    comment = guidance.observation
    next_action = guidance.recommendation
    collapse_state_label = None
    collapse_state_code: CollapseStateCode = "none"
    collapse_reason = None
    if dev25_pct >= 0:
        collapse_assessment = evaluate_collapse_state(
            latest=latest,
            vwap=vwap,
            ma5=ma5,
            ma5_prev1=ma5_prev1,
            ma5_slope=ma5_slope,
            ma5_slope_prev=ma5_slope_prev,
            ma5_slope_3d_ago=ma5_slope_3d_ago,
            ma25=ma25,
            ma25_prev5=ma25_prev5,
            atr14=atr14,
            day_open=day_open,
            day_high=day_high,
            day_low=day_low,
            day_close_position=day_close_position,
            volume_vs_avg20_pct=volume_vs_avg20_pct,
            high_breakout_count=high_breakout_count,
            low_higher_count=low_higher_count,
            high_breakouts=high_breakouts,
            low_highers=low_highers,
            previous_low=previous_low,
            recent20_low=recent20_low,
            ma75=ma75,
            recent60_low=recent60_low,
        )
        collapse_state_label = collapse_assessment.label
        collapse_state_code = collapse_assessment.code
        if collapse_assessment.is_alert:
            collapse_reason = collapse_assessment.reason
            next_action = "監視のみ"
    return TechnicalHeadlineSummary(
        rank=rank,
        rank_label=rank_label,
        comment=comment,
        next_action=next_action,
        ma25_position_label=position_label,
        collapse_state_label=collapse_state_label,
        collapse_state_code=collapse_state_code,
        reversal_state_label=reversal_state.label,
        reversal_state_code=reversal_state.code,
        collapse_reason=collapse_reason,
    )


def build_technical_position_assessment(
    *,
    latest: float,
    vwap: float,
    ma25: float,
    ma5: float | None = None,
    ma5_prev1: float | None = None,
    ma5_slope: float | None = None,
    ma5_slope_prev: float | None = None,
    ma5_slope_3d_ago: float | None = None,
    ma25_prev5: float | None = None,
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
    reversal_state_code: ReversalStateCode = "not_applicable",
) -> TechnicalPositionAssessment:
    """Score collapse risk and derive the single-stock hold judgement."""
    all_low_highers_failed = _all_false(low_highers)
    support_distance_atr = _nearest_support_distance_atr(
        latest=latest,
        atr14=atr14,
        supports=(ma25, previous_low, recent20_low, ma75, recent60_low),
    )
    support_is_near = support_distance_atr is not None and support_distance_atr <= 0.7
    risk = _score_collapse_risk(
        latest=latest,
        vwap=vwap,
        ma25=ma25,
        ma25_prev5=ma25_prev5,
        ma5=ma5,
        ma5_prev1=ma5_prev1,
        ma5_slope=ma5_slope,
        ma5_slope_prev=ma5_slope_prev,
        ma5_slope_3d_ago=ma5_slope_3d_ago,
        atr14=atr14,
        day_open=day_open,
        day_high=day_high,
        day_low=day_low,
        day_close_position=day_close_position,
        volume_vs_avg20_pct=volume_vs_avg20_pct,
        high_breakout_count=None,
        low_higher_count=None,
        high_breakouts=high_breakouts,
        low_highers=low_highers,
        previous_low=previous_low,
        recent20_low=recent20_low,
        ma75=ma75,
        recent60_low=recent60_low,
    )
    score = risk.score
    level = "低" if score <= 1 else "中" if score <= 3 else "高"

    ma25_up = latest >= ma25
    vwap_up = latest >= vwap
    ma25_near = atr14 not in (None, 0) and abs(latest - ma25) / atr14 <= 0.7
    any_low_higher = any(value is True for value in low_highers)
    close_is_low = day_close_position is not None and day_close_position < 0.5
    volume_is_low = volume_vs_avg20_pct is not None and volume_vs_avg20_pct < 80

    if not vwap_up and not ma25_up and all_low_highers_failed and risk.support_far:
        hold = "×"
    elif (vwap_up and not ma25_up) or close_is_low or volume_is_low:
        hold = "△"
    elif ma25_up and vwap_up and _gte(_position_pct(day_close_position), 50) and _gte(volume_vs_avg20_pct, 80) and support_is_near:
        hold = "◎"
    elif (ma25_up or ma25_near) and vwap_up and any_low_higher:
        hold = "○"
    else:
        hold = "△"

    # 表示ラベルをランク別に決定
    def _collapse_label_for(rank: TechnicalSummaryRank, s: int) -> str:
        primary_set = {"A1", "A1弱", "A2", "B1", "B2", "E"}
        if rank in primary_set:
            if s <= 1:
                return "崩れ軽微"
            if s <= 3:
                return "上値重い"
            return "崩れ警戒"
        if rank == "C1":
            if s <= 1:
                return "押し目候補"
            if s <= 3:
                return "VWAP回復待ち"
            return "押し目ではなく崩れ警戒"
        if rank == "D1":
            if s <= 1:
                return "戻り良好"
            if s <= 3:
                return "25日線奪回待ち"
            return "戻り売り警戒"
        # デフォルト
        if s <= 1:
            return "崩れ軽微"
        if s <= 3:
            return "上値重い"
        return "崩れ警戒"

    collapse_label = _collapse_label_for(headline_rank, score)

    return TechnicalPositionAssessment(
        collapse_risk_score=score,
        collapse_risk_level=level,
        collapse_risk_label=collapse_label,
        hold_judgement=hold,
        bottoming_start_established=(
            latest < ma25 and reversal_state_code == "reversal_confirmed"
        ),
        collapse_risk_reason=risk.collapse_risk_reason,
        collapse_risk_signals=risk.atoms,
    )


def build_collapse_score_brief(score: int | None) -> CollapseScoreBrief:
    return _COLLAPSE_SCORE_BRIEF_TABLE.resolve(score)


def build_technical_short_comment(
    *,
    rank: str,
    rank_label: str | None = None,
    entry_guidance: str | None = None,
    ma25_position_label: str | None = None,
    collapse_state_label: str | None = None,
    reversal_state_label: str | None = None,
    collapse_reason: str | None = None,
    ma5_slope: float | None = None,
    ma5_slope_prev: float | None = None,
    ma5_slope_3d_ago: float | None = None,
) -> str:
    ma5_comment = build_ma5_slope_short_comment(
        ma5_slope=ma5_slope,
        ma5_slope_prev=ma5_slope_prev,
        ma5_slope_3d_ago=ma5_slope_3d_ago,
    )
    display_label = rank_label or RANK_LABELS[rank]
    guidance = entry_guidance or SINGLE_STOCK_POSITION_DESCRIPTIONS[rank]
    parts = [f"{rank} {display_label}"]
    if collapse_state_label not in {None, "崩れ条件なし"}:
        parts.append(collapse_state_label)
    if reversal_state_label:
        parts.append(reversal_state_label)
    parts.append(guidance)
    if collapse_reason:
        parts.append(collapse_reason)
    parts.append(ma5_comment)
    return "｜".join(parts)


def build_ma5_slope_short_comment(
    *,
    ma5_slope: float | None = None,
    ma5_slope_prev: float | None = None,
    ma5_slope_3d_ago: float | None = None,
) -> str:
    details = _ma5_slope_comment_parts(
        ma5_slope=ma5_slope,
        ma5_slope_prev=ma5_slope_prev,
        ma5_slope_3d_ago=ma5_slope_3d_ago,
    )
    raw_score = _ma5_slope_score(
        ma5_slope=ma5_slope,
        ma5_slope_prev=ma5_slope_prev,
        ma5_slope_3d_ago=ma5_slope_3d_ago,
        capped=False,
    )
    if raw_score == 0:
        return "5日線良好"
    if raw_score == 4:
        return "5日線悪化"
    return "・".join(details)


def build_volume_comment(volume_vs_avg20_pct: float | None) -> str:
    if volume_vs_avg20_pct is None:
        return "出来高N/A"
    if volume_vs_avg20_pct < 60:
        return "出来高薄い"
    if volume_vs_avg20_pct < 80:
        return "出来高やや薄い"
    if volume_vs_avg20_pct < 120:
        return "出来高通常"
    if volume_vs_avg20_pct < 180:
        return "出来高伴う"
    return "出来高急増"


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


def _resolve_ma5_slope(
    ma5_slope: float | None,
    ma5: float | None,
    ma5_prev1: float | None,
) -> float | None:
    if ma5_slope is not None:
        return ma5_slope
    if ma5 is None or ma5_prev1 is None:
        return None
    return ma5 - ma5_prev1


def _ma5_slope_score(
    *,
    ma5_slope: float | None,
    ma5_slope_prev: float | None,
    ma5_slope_3d_ago: float | None,
    capped: bool,
) -> int:
    score = 0
    if ma5_slope is not None and ma5_slope <= 0:
        score += 2
    if ma5_slope is not None and ma5_slope_prev is not None and ma5_slope < ma5_slope_prev:
        score += 1
    if ma5_slope is not None and ma5_slope_3d_ago is not None and ma5_slope < ma5_slope_3d_ago:
        score += 1
    return min(score, 3) if capped else score


def _ma5_slope_comment_parts(
    *,
    ma5_slope: float | None,
    ma5_slope_prev: float | None,
    ma5_slope_3d_ago: float | None,
) -> tuple[str, ...]:
    parts: list[str] = []
    if ma5_slope is not None and ma5_slope <= 0:
        parts.append("5日線下向き")
    if ma5_slope is not None and ma5_slope_prev is not None and ma5_slope < ma5_slope_prev:
        parts.append("5日線鈍化")
    if ma5_slope is not None and ma5_slope_3d_ago is not None and ma5_slope < ma5_slope_3d_ago:
        parts.append("5日線失速")
    return tuple(parts)


def _position_pct(value: float | None) -> float | None:
    return None if value is None else value * 100


def _gte(value: float | int | None, threshold: float | int) -> bool:
    return value is not None and value >= threshold


def _gt(value: float | int | None, threshold: float | int) -> bool:
    return value is not None and value > threshold


def _has_b1_overheat_condition(
    *,
    three_session_change_pct: float | None,
    recent60_range_position: float | None,
    rsi14: float | None,
) -> bool:
    return any(
        (
            _gt(three_session_change_pct, 6),
            _gte(_position_pct(recent60_range_position), 80),
            _gte(rsi14, 70),
        )
    )


def _score_collapse_risk(
    *,
    latest: float,
    vwap: float,
    ma25: float | None,
    ma25_prev5: float | None,
    ma5: float | None,
    ma5_prev1: float | None,
    ma5_slope: float | None,
    ma5_slope_prev: float | None,
    ma5_slope_3d_ago: float | None,
    atr14: float | None,
    day_open: float | None,
    day_high: float | None,
    day_low: float | None,
    day_close_position: float | None,
    volume_vs_avg20_pct: float | None,
    high_breakout_count: int | None,
    low_higher_count: int | None,
    high_breakouts: tuple[bool | None, ...],
    low_highers: tuple[bool | None, ...],
    previous_low: float | None,
    recent20_low: float | None,
    ma75: float | None,
    recent60_low: float | None,
) -> _CollapseRiskSignals:
    support_distance_atr = _nearest_support_distance_atr(
        latest=latest,
        atr14=atr14,
        supports=(ma25, previous_low, recent20_low, ma75, recent60_low),
    )
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
    resolved_ma5_slope = _resolve_ma5_slope(ma5_slope, ma5, ma5_prev1)
    vwap_break = latest < vwap
    vwap_clear_break = atr14 not in (None, 0) and latest < vwap - 0.2 * atr14
    low_higher_failed = _all_false(low_highers) or (bool(low_highers) and low_higher_count == 0)
    high_breakout_failed = _all_false(high_breakouts) or (bool(high_breakouts) and high_breakout_count == 0)
    close_position_low = day_close_position is not None and day_close_position < 0.4
    volume_bearish_or_stalling = _gt(volume_vs_avg20_pct, 100) and bearish_or_stalling
    support_far = support_distance_atr is not None and support_distance_atr > 0.7
    ma25_slope_bad = _ma25_slope(ma25, ma25_prev5) == "down"
    ma5_down = resolved_ma5_slope is not None and resolved_ma5_slope <= 0

    return _CollapseRiskSignals(
        atoms=(
            SignalAtom("vwap_break", vwap_break, points=1),
            SignalAtom("vwap_clear_break", vwap_clear_break),
            SignalAtom("low_higher_failed", low_higher_failed, points=1),
            SignalAtom("high_breakout_failed", high_breakout_failed, points=1),
            # Terminal position remains an interaction diagnostic for T1/T3,
            # but is not scored as a standalone collapse signal.
            SignalAtom("close_position_low", close_position_low),
            SignalAtom("volume_bearish_or_stalling", volume_bearish_or_stalling, points=1),
            SignalAtom("support_far", support_far, points=1),
            SignalAtom("ma25_slope_bad", ma25_slope_bad),
            SignalAtom("ma5_down", ma5_down),
            SignalAtom(
                "ma5_slowing",
                resolved_ma5_slope is not None
                and ma5_slope_prev is not None
                and resolved_ma5_slope < ma5_slope_prev,
            ),
            SignalAtom(
                "ma5_stalling",
                resolved_ma5_slope is not None
                and ma5_slope_3d_ago is not None
                and resolved_ma5_slope < ma5_slope_3d_ago,
            ),
        ),
    )


def evaluate_collapse_state(
    *,
    latest: float,
    vwap: float,
    ma5: float | None,
    ma5_prev1: float | None,
    ma5_slope: float | None,
    ma5_slope_prev: float | None,
    ma5_slope_3d_ago: float | None,
    ma25: float | None,
    ma25_prev5: float | None,
    atr14: float | None,
    day_open: float | None,
    day_high: float | None,
    day_low: float | None,
    day_close_position: float | None,
    volume_vs_avg20_pct: float | None,
    high_breakout_count: int | None,
    low_higher_count: int | None,
    high_breakouts: tuple[bool | None, ...],
    low_highers: tuple[bool | None, ...],
    previous_low: float | None,
    recent20_low: float | None,
    ma75: float | None,
    recent60_low: float | None,
) -> CollapseStateAssessment:
    risk = _score_collapse_risk(
        latest=latest,
        vwap=vwap,
        ma25=ma25,
        ma25_prev5=ma25_prev5,
        ma5=ma5,
        ma5_prev1=ma5_prev1,
        ma5_slope=ma5_slope,
        ma5_slope_prev=ma5_slope_prev,
        ma5_slope_3d_ago=ma5_slope_3d_ago,
        atr14=atr14,
        day_open=day_open,
        day_high=day_high,
        day_low=day_low,
        day_close_position=day_close_position,
        volume_vs_avg20_pct=volume_vs_avg20_pct,
        high_breakout_count=high_breakout_count,
        low_higher_count=low_higher_count,
        high_breakouts=high_breakouts,
        low_highers=low_highers,
        previous_low=previous_low,
        recent20_low=recent20_low,
        ma75=ma75,
        recent60_low=recent60_low,
    )
    reason = risk.collapse_risk_reason
    is_alert = reason is not None
    if is_alert:
        code: CollapseStateCode = "collapse"
        label = "崩れ警戒"
    elif risk.score >= 2:
        code = "mild"
        label = "軽度警戒"
    elif risk.score >= 1:
        code = "attention"
        label = "要確認"
    else:
        code = "none"
        label = "崩れ条件なし"
    return CollapseStateAssessment(
        score=risk.score,
        code=code,
        label=label,
        is_alert=is_alert,
        reason=reason,
    )


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
    previous_low: float | None,
    recent20_low: float | None,
    ma75: float | None,
    recent60_low: float | None,
    low_highers: tuple[bool | None, ...],
) -> str:
    if atr14 in (None, 0) or day_low is None or day_high is None or day_open is None:
        return "none"
    supports = (previous_low, recent20_low, ma75, recent60_low)
    if _has_clearly_broken_support(
        latest=latest,
        day_low=day_low,
        atr14=atr14,
        supports=supports,
    ):
        return "exclude"
    support = _nearest_d2_support(
        day_low=day_low,
        atr14=atr14,
        supports=supports,
    )
    if support is None:
        return "none"
    close_position_pct = _position_pct(day_close_position)
    if not _gte(close_position_pct, 40):
        return "none"
    if latest < support + 0.1 * atr14:
        return "none"
    if not _has_direct_support(latest=latest, atr14=atr14, supports=supports):
        return "exclude"
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
    weak = _is_previous_low_standalone_support(
        support=support,
        atr14=atr14,
        previous_low=previous_low,
        recent20_low=recent20_low,
        ma75=ma75,
        recent60_low=recent60_low,
    )
    weak = weak or _has_two_of_three_lower_lows(low_highers)
    weak = weak or _is_moderate_volume_bearish(
        day_open=day_open,
        latest=latest,
        volume_vs_avg20_pct=volume_vs_avg20_pct,
    )

    score = _d2_auxiliary_score(
        latest=latest,
        day_open=day_open,
        day_high=day_high,
        day_low=day_low,
        support=support,
        volume_vs_avg20_pct=volume_vs_avg20_pct,
        rsi14=rsi14,
    )
    return "weak" if weak or score < 2 else "strong"


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


def _has_clearly_broken_support(
    *,
    latest: float,
    day_low: float,
    atr14: float,
    supports: tuple[float | None, ...],
) -> bool:
    return any(
        support is not None
        and day_low < support - 0.35 * atr14
        and latest < support
        for support in supports
    )


def _has_direct_support(
    *,
    latest: float,
    atr14: float,
    supports: tuple[float | None, ...],
) -> bool:
    return any(
        support is not None
        and support < latest
        and latest - support <= atr14
        for support in supports
    )


def _is_previous_low_standalone_support(
    *,
    support: float,
    atr14: float,
    previous_low: float | None,
    recent20_low: float | None,
    ma75: float | None,
    recent60_low: float | None,
) -> bool:
    if previous_low is None or abs(support - previous_low) > 0.000001:
        return False
    related_supports = (recent20_low, ma75, recent60_low)
    return not any(
        related is not None and abs(previous_low - related) <= 0.35 * atr14
        for related in related_supports
    )


def _has_two_of_three_lower_lows(low_highers: tuple[bool | None, ...]) -> bool:
    return sum(value is False for value in low_highers) >= 2


def build_d1_detail(*, ma25_distance_atr: float | None) -> tuple[str, str]:
    if ma25_distance_atr is None:
        return "D1", "判定保留"
    distance = abs(ma25_distance_atr)
    if distance <= 2.0:
        return "D1a", "戻り途中・25日線接近"
    return "D1b", "戻り途中・25日線遠い"


def build_d2_detail(
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
    previous_low: float | None,
    recent20_low: float | None,
    ma75: float | None,
    recent60_low: float | None,
    low_highers: tuple[bool | None, ...] = (),
) -> tuple[str, str]:
    evaluation = _evaluate_d2_bottoming_candidate(
        latest=latest,
        vwap=vwap,
        day_open=day_open,
        day_high=day_high,
        day_low=day_low,
        day_close_position=day_close_position,
        atr14=atr14,
        volume_vs_avg20_pct=volume_vs_avg20_pct,
        rsi14=rsi14,
        previous_low=previous_low,
        recent20_low=recent20_low,
        ma75=ma75,
        recent60_low=recent60_low,
        low_highers=low_highers,
    )
    if evaluation == "weak":
        return "D2弱", "底打ち候補・弱"
    return "D2", "底打ち候補"


def build_d3_detail(
    *,
    volume_vs_avg20_pct: float | None,
    high_breakout_count: int | None = None,
    day_close_position: float | None = None,
) -> tuple[str, str]:
    if _gte(high_breakout_count, 1):
        return "D3強", "VWAP維持・高値更新"
    if _gte(_position_pct(day_close_position), 70):
        return "D3強", "VWAP維持・終端強い"
    if volume_vs_avg20_pct is None:
        return "D3", "VWAP維持・出来高N/A"
    if volume_vs_avg20_pct >= 80:
        return "D3強", "VWAP維持・出来高伴う"
    if volume_vs_avg20_pct >= 60:
        return "D3", "VWAP維持・出来高やや不足"
    return "D3弱", "反転形あるも出来高不足"


def build_dev25_risk_label(rank: str, dev25_pct: float) -> str | None:
    if rank == "D2":
        if dev25_pct >= -8:
            return "浅押し反発候補"
        if dev25_pct >= -15:
            return "底打ち候補"
        return "深掘れ反発候補・リスク大"
    if rank == "D3":
        if dev25_pct >= -4:
            return "25日線奪回接近"
        if dev25_pct >= -8:
            return "反転初動"
        if dev25_pct >= -15:
            return "大幅乖離からの反転"
        return "急落リバ・戻り売り警戒"
    return None


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
    return _gt(volume_vs_avg20_pct, 150) and latest < day_open and body_ratio >= 0.65


def _is_moderate_volume_bearish(
    *,
    day_open: float,
    latest: float,
    volume_vs_avg20_pct: float | None,
) -> bool:
    return (
        volume_vs_avg20_pct is not None
        and 100 <= volume_vs_avg20_pct <= 150
        and latest < day_open
    )


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
    return upper_wick / day_range >= UPPER_STALL_WICK_RATIO and upper_wick >= body * 1.5


__all__ = [
    "RANK_LABELS",
    "RANK_ORDER",
    "SINGLE_STOCK_POSITION_DESCRIPTIONS",
    "BacktestEntryGuidance",
    "CollapseStateAssessment",
    "ReversalStateAssessment",
    "build_collapse_score_brief",
    "build_d1_detail",
    "build_d2_detail",
    "build_d3_detail",
    "build_d_detail_headline",
    "build_dev25_risk_label",
    "build_ma5_slope_short_comment",
    "build_technical_headline_summary",
    "build_technical_position_assessment",
    "build_technical_short_comment",
    "build_volume_comment",
    "build_technical_strategy_lines",
    "build_nearby_resistance_lines",
    "build_nearby_support_lines",
    "classify_ma25_position_band",
    "classify_backtest_entry_guidance",
    "classify_position_rank",
    "classify_technical_summary_rank",
    "evaluate_collapse_state",
    "evaluate_reversal_state",
]
