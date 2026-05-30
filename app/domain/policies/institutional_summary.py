"""Domain policies for institutional investment summary."""

from __future__ import annotations

from app.domain.models.institutional_summary import (
    InstitutionalScoreBreakdown,
    InstitutionalSummary,
    MarketCapClass,
    TechnicalConditionSummary,
    TechnicalSignal,
)

YEN_PER_OKU = 100_000_000
YEN_PER_CHO = 1_000_000_000_000


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
    if market_cap_yen is None:
        return 0
    value = float(market_cap_yen)
    if value >= 3 * YEN_PER_CHO:
        return 5
    if value >= 1 * YEN_PER_CHO:
        return 4
    if value >= 5000 * YEN_PER_OKU:
        return 3
    if value >= 2000 * YEN_PER_OKU:
        return 2
    if value >= 1000 * YEN_PER_OKU:
        return 1
    return 0


def score_trading_value(trading_value_yen: float | int | None) -> int:
    if trading_value_yen is None:
        return 0
    value_oku = float(trading_value_yen) / YEN_PER_OKU
    if value_oku >= 100:
        return 5
    if value_oku >= 50:
        return 4
    if value_oku >= 20:
        return 3
    if value_oku >= 10:
        return 2
    if value_oku >= 5:
        return 1
    return 0


def score_roic(roic_pct: float | int | None) -> int:
    if roic_pct is None:
        return 0
    value = float(roic_pct)
    if value >= 15:
        return 5
    if value >= 10:
        return 4
    if value >= 8:
        return 3
    if value >= 5:
        return 2
    if value >= 3:
        return 1
    return 0


def score_eps_cagr(eps_cagr_pct: float | int | None) -> int:
    if eps_cagr_pct is None:
        return 0
    value = float(eps_cagr_pct)
    if value >= 20:
        return 5
    if value >= 10:
        return 4
    if value >= 5:
        return 3
    if value >= 0:
        return 2
    if value >= -5:
        return 1
    return 0


def build_technical_signal(latest: float | int | None, reference: float | int | None) -> TechnicalSignal:
    if latest is None or reference is None:
        return "N/A"
    return "○" if float(latest) > float(reference) else "×"


def build_technical_condition_summary(
    *,
    latest: float | int | None,
    vwap: float | int | None,
    ma5: float | int | None,
    ma25: float | int | None,
    vwap_is_daily_reference: bool = False,
) -> TechnicalConditionSummary:
    return TechnicalConditionSummary(
        vwap=build_technical_signal(latest, vwap),
        ma5=build_technical_signal(latest, ma5),
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
    ma5: float | int | None,
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
            ma5=ma5,
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
