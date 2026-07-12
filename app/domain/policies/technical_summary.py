"""Domain policy: technical summary ranks and nearby price lines."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.models.signal_atom import SignalAtom, score_signal_atoms
from app.domain.models.technical_summary import (
    Ma25PositionBandCode,
    TechnicalHeadlineSummary,
    TechnicalPositionAssessment,
    TechnicalSummaryLine,
    TechnicalSummaryRank,
)
from app.domain.policies.range_table import RangeBand, RangeTable

RANK_LABELS: dict[TechnicalSummaryRank, str] = {
    "B2": "極端乖離",
    "B1": "高収益・高リスク",
    "A2": "高モメンタム",
    "A1": "上昇優位",
    "A1弱": "初期逆行注意",
    "C2": "崩れ警戒",
    "C1": "25日線接近",
    "D1": "戻り途中",
    "D2": "底打ち候補",
    "D3": "底打ち初動",
    "E": "下落トレンド",
}

RANK_ORDER: tuple[TechnicalSummaryRank, ...] = (
    "B2",
    "B1",
    "A2",
    "A1",
    "A1弱",
    "C2",
    "C1",
    "D1",
    "D2",
    "D3",
    "E",
)

HEADLINE_COMMENTS: dict[TechnicalSummaryRank, str] = {
    "B2": "新規買い非推奨。利確優先。",
    "B1": "上昇余地はあるが逆行リスクも高い。",
    "A2": "高モメンタム。上昇継続を確認。",
    "A1": "順張り候補。位置良好。",
    "A1弱": "中期上昇余地はあるが、短期下振れに注意。",
    "C2": "25日線割れ警戒。買いは待ち。",
    "C1": "方向未確定。",
    "D1": "25日線奪回待ち。上値確認中。",
    "D2": "支持線反発待ち。",
    "D3": "VWAP回復。安値切り上げ・反転確認。",
    "E": "買い見送り。反転確認待ち。",
}

SINGLE_STOCK_POSITION_DESCRIPTIONS: dict[TechnicalSummaryRank, str] = {
    "B2": "上値余地より、逆行リスクが高い位置",
    "B1": "高収益を狙えるが、逆行リスクも高い。",
    "A2": "高モメンタム。上昇継続候補。",
    "A1": "安定上昇または中期モメンタムの買い候補",
    "A1弱": "中期上昇余地はあるが、初期逆行に注意。",
    "C1": "方向未確定",
    "C2": "監視のみ",
    "D1": HEADLINE_COMMENTS["D1"],
    "D2": HEADLINE_COMMENTS["D2"],
    "D3": HEADLINE_COMMENTS["D3"],
    "E": HEADLINE_COMMENTS["E"],
}

NEXT_ACTIONS: dict[TechnicalSummaryRank, str] = {
    "B2": "短期監視のみ。追加買い不可。",
    "B1": "高値追い注意。深押し待ち。",
    "A2": "高値追いは抑え、VWAP維持を確認。",
    "A1": "支持線・VWAP維持を確認。",
    "A1弱": "VWAP回復・支持線維持を確認。",
    "C2": "VWAP回復後も15分維持を確認。追加買い不可。",
    "C1": "過熱はないが方向確認。",
    "D1": "25日線接近時の利確圧に注意。追加買いは25日線奪回後。",
    "D2": "まだ入らない。VWAP回復待ち。",
    "D3": "小さく入れる候補。通常サイズは25日線奪回後。",
    "E": "監視のみ。新規買い不可。",
}


@dataclass(frozen=True)
class Ma25PositionBand:
    code: Ma25PositionBandCode
    label: str
    comment: str


_MA25_POSITION_BAND_TABLE = RangeTable[Ma25PositionBand](
    bands=(
        RangeBand(14, Ma25PositionBand("extreme", "極端乖離帯", "上値余地より逆行リスクを優先。")),
        RangeBand(10, Ma25PositionBand("high_risk", "高収益・高リスク帯", "上昇余地はあるが逆行リスクも高い。")),
        RangeBand(8, Ma25PositionBand("high_momentum", "高モメンタム帯", "高モメンタム。上昇継続を確認。")),
        RangeBand(6, Ma25PositionBand("medium_momentum", "中期モメンタム帯", "中期上昇優位の順張り候補。")),
        RangeBand(4, Ma25PositionBand("initial_pullback_risk", "初期逆行注意帯", "中期上昇余地はあるが、短期下振れに注意。")),
        RangeBand(2, Ma25PositionBand("stable", "安定上昇帯", "短期逆行が比較的少ない安定型の買い候補。")),
        RangeBand(0, Ma25PositionBand("near_ma25", "25日線接近帯", "短期のみ微優位。方向確認を優先。")),
        RangeBand(-2, Ma25PositionBand("just_below", "25日線直下・統計的不利", "25日線直下は統計的に不利。反転確認を優先。")),
    ),
    default=Ma25PositionBand("below", "25日線下", "25日線奪回または反転確認を優先。"),
)


def classify_ma25_position_band(dev25_pct: float) -> Ma25PositionBand:
    return _MA25_POSITION_BAND_TABLE.resolve(dev25_pct)

D_DETAIL_MAIN_JUDGEMENTS: dict[str, str] = {
    "D1a": "監視優先。D3化なら小さく可",
    "D1b": "監視優先。深指値は原則不可",
    "D1": "判定保留。新規不可",
    "D2": "支持線反発候補。原則VWAP回復待ち",
    "D2弱": "支持線根拠が弱い。VWAP回復まで監視",
    "D3強": "小さく可。D3内で最有力",
    "D3": "小さく可。出来高確認",
    "D3弱": "監視寄り。出来高不足",
}


@dataclass(frozen=True)
class _RankingCollapseAssessment:
    score: int
    label: str
    c2_fall: bool
    c2_fall_reason: str | None


@dataclass(frozen=True)
class CollapseScoreBrief:
    label: str
    comment: str

    @property
    def text(self) -> str:
        return f"{self.label}｜{self.comment}"


_COLLAPSE_SCORE_BRIEF_TABLE = RangeTable[CollapseScoreBrief](
    bands=(
        RangeBand(6, CollapseScoreBrief("ほぼ触らない", "構造回復まで見送り")),
        RangeBand(5, CollapseScoreBrief("かなり回避", "例外条件が揃う時だけ短期リバ検討")),
        RangeBand(4, CollapseScoreBrief("原則回避", "新規買い回避。前場深押し指値は避ける")),
        RangeBand(2, CollapseScoreBrief("条件付き候補", "後場VWAP上維持・終端60%以上を確認")),
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
    "A1弱": (
        "前場深押し○：支持線付近 {support_range}円で検討。VWAP回復・維持を確認。",
        "前場VWAP回復○：VWAP回復＋15分以上維持なら小さく検討可。",
        "後場VWAP回復○：後場VWAP上維持ならエントリー候補。支持線割れは見送り。",
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
        "前場深押し×：崩れ条件あり。深押し指値は避け、支持線維持を確認する。",
        "前場VWAP回復×：VWAP回復だけでは根拠不足。安値切り上げと高値更新を確認する。",
        "後場VWAP回復△：後場VWAP上維持＋安値切り上げなら小さく検討可。慎重なら崩れ条件の解消を待つ。",
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

def build_technical_strategy_lines(
    rank: TechnicalSummaryRank,
    *,
    support_range: str = "N/A",
    nearest_support: str = "N/A",
    detail_code: str | None = None,
    support_entry_range: str = "N/A",
    support_pullback_range: str = "N/A",
    vwap_recovery_range: str = "N/A",
    vwap_pullback_range: str = "N/A",
    risk_reward: str = "RR算出不可",
) -> tuple[str, ...]:
    if rank == "D1":
        return _build_d1_strategy_lines(
            detail_code=detail_code or "D1",
            support_entry_range=support_entry_range,
            nearest_support=nearest_support,
            risk_reward=risk_reward,
        )
    if rank == "D2":
        prefix = "D2弱｜支持線根拠弱い｜" if detail_code == "D2弱" else ""
        return (
            f"前場深押し△：{prefix}地合い良好時のみ {support_entry_range}。RR1.5以上なら試し可（{risk_reward}）。安全重視ならVWAP回復確認。",
            f"前場VWAP回復△：VWAP15分維持なら試し玉候補 {vwap_recovery_range}。安値切り上げ・高値更新・終端60%以上が揃いD3化すれば○。出来高60%以上が望ましい。",
            "後場VWAP回復△〜○：後場VWAP上維持かつ終端60%以上なら小さく可。当日高値圏でなければ持ち越しは弱い。",
        )
    if rank == "D3":
        return _build_d3_strategy_lines(
            detail_code=detail_code or "D3",
            support_pullback_range=support_pullback_range,
            vwap_recovery_range=vwap_recovery_range,
            vwap_pullback_range=vwap_pullback_range,
            nearest_support=nearest_support,
            risk_reward=risk_reward,
        )
    templates = STRATEGY_LINES[rank]
    if templates is None:
        return ("N/A（判定基準未設定）",)
    return tuple(
        template.format(support_range=support_range, nearest_support=nearest_support)
        for template in templates
    )


def build_d_detail_headline(
    rank: TechnicalSummaryRank,
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
    support_entry_range: str,
    nearest_support: str,
    risk_reward: str,
) -> tuple[str, ...]:
    if detail_code == "D1a":
        rr_text = "RR算出不可" if risk_reward == "RR算出不可" else f"{risk_reward}で判定"
        return (
            f"前場深押し△：地合い良好なら {support_entry_range}。25日線または直近抵抗線までの{rr_text}。安全重視ならVWAP再回復確認。",
            "前場VWAP回復△：VWAP回復だけでは不可。VWAP15分維持＋安値切り上げ＋高値更新でD3化なら小さく可。",
            "後場VWAP回復△：後場VWAP上維持なら小さく可。25日線接近時は利確圧に注意し、持ち越しは25日線手前で評価。",
        )
    if detail_code == "D1b":
        if nearest_support == "N/A":
            deep_order = "前場深押し×：支持線不明のため深指値不可。"
        else:
            deep_order = f"前場深押し×〜△：基本は危険。支持線 {nearest_support}円が明確でRR2.0以上なら最小ロットのみ（{risk_reward}）。25日線まで遠く戻り確認不足。"
        return (
            deep_order,
            "前場VWAP回復△：VWAP上でもD3未達なら監視。入るならD3条件成立後。",
            "後場VWAP回復△〜×：回復だけでは持ち越しは弱い。出来高60%以上かつ終端60%以上がなければ見送り。",
        )
    return (
        "前場深押し×：ATR距離不明のため指値算出不可。",
        "前場VWAP回復△：D3条件を満たせば小さく可。ただし25日線距離不明のため通常サイズ不可。",
        "後場VWAP回復△〜×：判定材料不足。後場エントリーは原則見送り。",
    )


def _build_d3_strategy_lines(
    *,
    detail_code: str,
    support_pullback_range: str,
    vwap_recovery_range: str,
    vwap_pullback_range: str,
    nearest_support: str,
    risk_reward: str,
) -> tuple[str, ...]:
    if detail_code == "D3強":
        rr_text = "RR算出不可" if risk_reward == "RR算出不可" else f"{risk_reward}が良好なら可"
        return (
            f"前場深押し○：押し目待ちは {vwap_pullback_range} または {support_pullback_range}。{rr_text}。",
            "前場VWAP回復◎：最有力。VWAP15分維持＋出来高80%以上で小さく可。通常サイズは25日線奪回後。",
            "後場VWAP回復◎：後場VWAP上維持なら持ち越し候補。25日線未満のためサイズは抑える。",
        )
    if detail_code == "D3弱":
        if nearest_support == "N/A":
            deep_order = "前場深押し×：支持線不明のため深指値不可。"
        else:
            deep_order = f"前場深押し△：支持線 {nearest_support}円近辺のみ。上に飛びつかず、RR2.0以上で最小ロット（{risk_reward}）。"
        return (
            deep_order,
            "前場VWAP回復△：形はあるが出来高不足。前日高値試しまたは終端70%以上なら小さく可。",
            "後場VWAP回復△〜×：持ち越しは弱い。後場VWAP維持でも出来高が戻らなければ監視継続。",
        )
    return (
        f"前場深押し○〜△：押し目は {support_pullback_range}。出来高不足で継続力は弱く、RR1.5未満なら見送り（{risk_reward}）。",
        f"前場VWAP回復○：小さく可 {vwap_recovery_range}。出来高増加または前日高値試しで信頼度を上げる。",
        "後場VWAP回復○〜△：後場VWAP上維持なら可。出来高不足またはN/Aなら持ち越しは慎重。",
    )


def classify_technical_summary_rank(
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
) -> TechnicalSummaryRank:
    vwap_up = latest > vwap
    close_position_pct = _position_pct(day_close_position)

    if dev25_pct >= 14 or (dev25_pct >= 10 and _gt(ma25_distance_atr, 3.0)):
        return "B2"

    if 10 <= dev25_pct < 14:
        return "B1"

    if dev25_pct >= 0:
        collapse_assessment = _evaluate_above_ma25_ranking_collapse(
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
        if collapse_assessment.c2_fall:
            return "C2"
        if dev25_pct >= 8:
            return "A2"
        if dev25_pct >= 6:
            return "A1"
        if dev25_pct >= 4:
            return "A1弱"
        if dev25_pct >= 2:
            return "A1"
        return "C1"

    if vwap_up:
        if (
            _gte(low_higher_count, 2)
            and _gte(close_position_pct, 60)
            and vwap_maintained_15m is True
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
        previous_low=previous_low,
        recent20_low=recent20_low,
        ma75=ma75,
        recent60_low=recent60_low,
        low_highers=low_highers,
    )
    if d2_evaluation == "exclude":
        return "E"
    if d2_evaluation in {"strong", "weak"}:
        return "D2"
    return "E"


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
    rank = classify_technical_summary_rank(
        dev25_pct=dev25_pct,
        latest=latest,
        vwap=vwap,
        ma25_distance_atr=ma25_distance_atr,
        ma5=ma5,
        ma5_prev1=ma5_prev1,
        ma5_slope=ma5_slope,
        ma5_slope_prev=ma5_slope_prev,
        ma5_slope_3d_ago=ma5_slope_3d_ago,
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
        vwap_maintained_15m=vwap_maintained_15m,
        low_highers=low_highers,
        high_breakouts=high_breakouts,
    )
    position_band = classify_ma25_position_band(dev25_pct)
    overheated = _has_b1_overheat_condition(
        three_session_change_pct=three_session_change_pct,
        recent60_range_position=recent60_range_position,
        rsi14=rsi14,
        day_close_position=day_close_position,
    )
    position_label = position_band.label
    if 8 <= dev25_pct < 10 and overheated:
        position_label += "（過熱兆候あり）"
    comment = position_band.comment if dev25_pct >= 0 and rank != "C2" else HEADLINE_COMMENTS[rank]
    next_action = NEXT_ACTIONS[rank]
    collapse_state_label = None
    c2_fall_reason = None
    if dev25_pct >= 0:
        collapse_assessment = _evaluate_above_ma25_ranking_collapse(
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
        if rank == "C2":
            c2_fall_reason = collapse_assessment.c2_fall_reason
    return TechnicalHeadlineSummary(
        rank=rank,
        rank_label=RANK_LABELS[rank],
        comment=comment,
        next_action=next_action,
        ma25_position_label=position_label,
        collapse_state_label=collapse_state_label,
        c2_fall_reason=c2_fall_reason,
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
        primary_set = {"A1", "A1弱", "A2", "B1", "B2", "D2", "D3", "E"}
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
        if rank == "C2":
            if s <= 1:
                return "軽度崩れ"
            if s <= 3:
                return "崩れ警戒"
            return "買い不可"
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
        bottoming_start_established=latest < ma25 and headline_rank == "D3",
        collapse_risk_reason=risk.collapse_risk_reason,
        collapse_risk_signals=risk.atoms,
    )


def build_collapse_score_brief(score: int | None) -> CollapseScoreBrief:
    return _COLLAPSE_SCORE_BRIEF_TABLE.resolve(score)


def build_technical_short_comment(
    *,
    rank: TechnicalSummaryRank,
    ma25_position_label: str | None = None,
    collapse_state_label: str | None = None,
    c2_fall_reason: str | None = None,
    ma5_slope: float | None = None,
    ma5_slope_prev: float | None = None,
    ma5_slope_3d_ago: float | None = None,
) -> str:
    ma5_comment = build_ma5_slope_short_comment(
        ma5_slope=ma5_slope,
        ma5_slope_prev=ma5_slope_prev,
        ma5_slope_3d_ago=ma5_slope_3d_ago,
    )
    c2_reason_part = _format_c2_reason_part(rank, c2_fall_reason)
    position = (
        ma25_position_label
        if ma25_position_label and rank not in {"C2", "D1", "D2", "D3", "E"}
        else SINGLE_STOCK_POSITION_DESCRIPTIONS[rank]
    )
    below_ma25_warning = (
        "｜25日線直下・統計的不利"
        if ma25_position_label == "25日線直下・統計的不利" and rank in {"D1", "D2", "D3", "E"}
        else ""
    )
    return f"{rank} {RANK_LABELS[rank]} {position}{c2_reason_part}{below_ma25_warning}｜{ma5_comment}"


def _format_c2_reason_part(rank: TechnicalSummaryRank, c2_fall_reason: str | None) -> str:
    if rank != "C2" or not c2_fall_reason:
        return ""
    if "：" in c2_fall_reason:
        return f"｜{c2_fall_reason}"
    return f"｜C2陥落トリガー：{c2_fall_reason}"


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
    day_close_position: float | None,
) -> bool:
    return any(
        (
            _gt(three_session_change_pct, 6),
            _gte(_position_pct(recent60_range_position), 80),
            _gte(rsi14, 70),
            _gte(_position_pct(day_close_position), 85),
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
            SignalAtom("close_position_low", close_position_low, points=1),
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


def _evaluate_above_ma25_ranking_collapse(
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
) -> _RankingCollapseAssessment:
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
    c2_fall_reason = risk.collapse_risk_reason
    c2_fall = c2_fall_reason is not None
    if c2_fall:
        label = "崩れ警戒"
    elif risk.score >= 2:
        label = "軽度警戒"
    elif risk.score >= 1:
        label = "要確認"
    else:
        label = "崩れ条件なし"
    return _RankingCollapseAssessment(
        score=risk.score,
        label=label,
        c2_fall=c2_fall,
        c2_fall_reason=c2_fall_reason,
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


def build_dev25_risk_label(rank: TechnicalSummaryRank, dev25_pct: float) -> str | None:
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
            return "深押し反転"
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
    "classify_technical_summary_rank",
]
