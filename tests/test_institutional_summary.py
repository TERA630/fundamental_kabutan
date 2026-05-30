import pytest

from app.domain.policies.institutional_summary import (
    YEN_PER_OKU,
    YEN_PER_CHO,
    build_institutional_summary,
    build_technical_condition_summary,
    calc_trading_value_yen,
    calc_volume_vs_avg20_pct,
    classify_market_cap,
    score_eps_cagr,
    score_market_cap,
    score_roic,
    score_trading_value,
)


def test_score_market_cap_thresholds():
    assert score_market_cap(3 * YEN_PER_CHO) == 5
    assert score_market_cap(1 * YEN_PER_CHO) == 4
    assert score_market_cap(5000 * YEN_PER_OKU) == 3
    assert score_market_cap(2000 * YEN_PER_OKU) == 2
    assert score_market_cap(1000 * YEN_PER_OKU) == 1
    assert score_market_cap(999 * YEN_PER_OKU) == 0
    assert score_market_cap(None) == 0


def test_score_trading_value_thresholds():
    assert score_trading_value(100 * YEN_PER_OKU) == 5
    assert score_trading_value(50 * YEN_PER_OKU) == 4
    assert score_trading_value(20 * YEN_PER_OKU) == 3
    assert score_trading_value(10 * YEN_PER_OKU) == 2
    assert score_trading_value(5 * YEN_PER_OKU) == 1
    assert score_trading_value(4.99 * YEN_PER_OKU) == 0
    assert score_trading_value(None) == 0


def test_score_roic_and_eps_cagr_thresholds():
    assert score_roic(15) == 5
    assert score_roic(10) == 4
    assert score_roic(8) == 3
    assert score_roic(5) == 2
    assert score_roic(3) == 1
    assert score_roic(2.9) == 0
    assert score_roic(None) == 0

    assert score_eps_cagr(20) == 5
    assert score_eps_cagr(10) == 4
    assert score_eps_cagr(5) == 3
    assert score_eps_cagr(0) == 2
    assert score_eps_cagr(-5) == 1
    assert score_eps_cagr(-5.1) == 0
    assert score_eps_cagr(None) == 0


def test_calc_trading_value_and_volume_average_ratio():
    assert calc_trading_value_yen(2000, 1_000_000) == 2_000_000_000
    assert calc_trading_value_yen(None, 1_000_000) is None
    assert calc_volume_vs_avg20_pct(1_200_000, 1_000_000) == pytest.approx(20.0)
    assert calc_volume_vs_avg20_pct(1_000_000, 0) is None


def test_classify_market_cap():
    assert classify_market_cap(3 * YEN_PER_CHO) == "超大型"
    assert classify_market_cap(1 * YEN_PER_CHO) == "大型主役"
    assert classify_market_cap(2000 * YEN_PER_OKU) == "中型主役"
    assert classify_market_cap(1999 * YEN_PER_OKU) == "小型"
    assert classify_market_cap(None) is None


def test_build_technical_condition_summary():
    summary = build_technical_condition_summary(
        latest=101,
        vwap=100,
        ma5=102,
        ma25=None,
        vwap_is_daily_reference=True,
    )

    assert summary.vwap == "○"
    assert summary.ma5 == "×"
    assert summary.ma25 == "N/A"
    assert summary.vwap_is_daily_reference is True


def test_build_institutional_summary_keeps_fundamental_and_technical_out_of_score():
    summary = build_institutional_summary(
        market_cap_yen=3 * YEN_PER_CHO,
        close=2000,
        volume=10_000_000,
        volume_avg20=8_000_000,
        roic_pct=15,
        eps_cagr_pct=20,
        fundamental_score=80,
        fundamental_rank="S",
        latest=2100,
        vwap=2000,
        ma5=2050,
        ma25=2150,
    )

    assert summary.trading_value_yen == 20_000_000_000
    assert summary.volume_vs_avg20_pct == pytest.approx(25.0)
    assert summary.market_cap_class == "超大型"
    assert summary.score.total == 20
    assert summary.fundamental_score == 80
    assert summary.fundamental_rank == "S"
    assert summary.technical.vwap == "○"
    assert summary.technical.ma5 == "○"
    assert summary.technical.ma25 == "×"
