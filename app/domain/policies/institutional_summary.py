"""Domain policies for institutional investment summary."""

from __future__ import annotations

from app.domain.models.institutional_summary import (
    InstitutionalScoreBreakdown,
    InstitutionalSummary,
    MarketCapClass,
    TechnicalConditionSummary,
    TechnicalSignal,
)
from app.domain.policies.range_table import RangeBand, RangeTable

YEN_PER_OKU = 100_000_000
YEN_PER_CHO = 1_000_000_000_000


MARKET_CAP_SCORE_TABLE = RangeTable(
    bands=(
        RangeBand(3 * YEN_PER_CHO, 5),
        RangeBand(1 * YEN_PER_CHO, 4),
        RangeBand(5000 * YEN_PER_OKU, 3),
        RangeBand(2000 * YEN_PER_OKU, 2),
        RangeBand(1000 * YEN_PER_OKU, 1),
    ),
    default=0,
)

TRADING_VALUE_SCORE_TABLE = RangeTable(
    bands=(
        RangeBand(100 * YEN_PER_OKU, 5),
        RangeBand(50 * YEN_PER_OKU, 4),
        RangeBand(20 * YEN_PER_OKU, 3),
        RangeBand(10 * YEN_PER_OKU, 2),
        RangeBand(5 * YEN_PER_OKU, 1),
    ),
    default=0,
)

ROIC_SCORE_TABLE = RangeTable(
    bands=(
        RangeBand(15, 5),
        RangeBand(10, 4),
        RangeBand(8, 3),
        RangeBand(5, 2),
        RangeBand(3, 1),
    ),
    default=0,
)

EPS_CAGR_SCORE_TABLE = RangeTable(
    bands=(
        RangeBand(20, 5),
        RangeBand(10, 4),
        RangeBand(5, 3),
        RangeBand(0, 2),
        RangeBand(-5, 1),
    ),
    default=0,
)


def calc_trading_value_yen(close: float | int | None, volume: float | int | None) -> float | None:
    if close is None or volume is None:
        return None
    return float(close) * float(volume)


def calc_volume_vs_avg20_pct(volume: float | int | None, volume_avg20: float | int | None) -> float | None:
    if volume is None or volume_avg20 in (None, 0):
        return None
    return ((float(volume) / float(volume_avg20)) - 1) * 100


def classify_market_cap(market_cap_yen: float | int | None) -> MarketCapClass | None:
    if market_cap_yen is None:
        return None
    value = float(market_cap_yen)
    if value >= 3 * YEN_PER_CHO:
        return "超大型"
    if value >= 1 * YEN_PER_CHO:
        return "大型主役"
    if value >= 2000 * YEN_PER_OKU:
        return "中型主役"
    return "小型"


def score_market_cap(market_cap_yen: float | int | None) -> int:
    return MARKET_CAP_SCORE_TABLE.resolve(market_cap_yen)


def score_trading_value(trading_value_yen: float | int | None) -> int:
    return TRADING_VALUE_SCORE_TABLE.resolve(trading_value_yen)


def score_roic(roic_pct: float | int | None) -> int:
    return ROIC_SCORE_TABLE.resolve(roic_pct)


def score_eps_cagr(eps_cagr_pct: float | int | None) -> int:
    return EPS_CAGR_SCORE_TABLE.resolve(eps_cagr_pct)


def build_technical_signal(latest: float | int | None, reference: float | int | None) -> TechnicalSignal:
    if latest is None or reference is None:
        return "N/A"
    return "○" if float(latest) > float(reference) else "×"


def build_technical_condition_summary(
    *,
    latest: float | int | None,
    vwap: float | int | None,
    ma25: float | int | None,
    vwap_is_daily_reference: bool = False,
) -> TechnicalConditionSummary:
    return TechnicalConditionSummary(
        vwap=build_technical_signal(latest, vwap),
        ma25=build_technical_signal(latest, ma25),
        vwap_is_daily_reference=vwap_is_daily_reference,
    )


def build_institutional_score(
    *,
    market_cap_yen: float | int | None,
    trading_value_yen: float | int | None,
    roic_pct: float | int | None,
    eps_cagr_pct: float | int | None,
) -> InstitutionalScoreBreakdown:
    return InstitutionalScoreBreakdown(
        market_cap=score_market_cap(market_cap_yen),
        trading_value=score_trading_value(trading_value_yen),
        roic=score_roic(roic_pct),
        eps_cagr=score_eps_cagr(eps_cagr_pct),
    )


def build_institutional_summary(
    *,
    market_cap_yen: float | int | None,
    close: float | int | None,
    volume: float | int | None,
    volume_avg20: float | int | None,
    roic_pct: float | int | None,
    eps_cagr_pct: float | int | None,
    fundamental_score: int | None,
    fundamental_rank: str | None,
    latest: float | int | None,
    vwap: float | int | None,
    ma25: float | int | None,
    vwap_is_daily_reference: bool = False,
) -> InstitutionalSummary:
    trading_value_yen = calc_trading_value_yen(close, volume)
    return InstitutionalSummary(
        market_cap_yen=float(market_cap_yen) if market_cap_yen is not None else None,
        market_cap_class=classify_market_cap(market_cap_yen),
        volume=float(volume) if volume is not None else None,
        volume_avg20=float(volume_avg20) if volume_avg20 is not None else None,
        volume_vs_avg20_pct=calc_volume_vs_avg20_pct(volume, volume_avg20),
        trading_value_yen=trading_value_yen,
        score=build_institutional_score(
            market_cap_yen=market_cap_yen,
            trading_value_yen=trading_value_yen,
            roic_pct=roic_pct,
            eps_cagr_pct=eps_cagr_pct,
        ),
        fundamental_score=fundamental_score,
        fundamental_rank=fundamental_rank,
        technical=build_technical_condition_summary(
            latest=latest,
            vwap=vwap,
            ma25=ma25,
            vwap_is_daily_reference=vwap_is_daily_reference,
        ),
    )


__all__ = [
    "YEN_PER_CHO",
    "YEN_PER_OKU",
    "build_institutional_score",
    "build_institutional_summary",
    "build_technical_condition_summary",
    "build_technical_signal",
    "calc_trading_value_yen",
    "calc_volume_vs_avg20_pct",
    "classify_market_cap",
    "score_eps_cagr",
    "score_market_cap",
    "score_roic",
    "score_trading_value",
]
