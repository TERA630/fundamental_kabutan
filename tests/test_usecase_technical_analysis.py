import pandas as pd
import pytest

from app.domain.usecases.technical_analysis import (
    TechnicalAnalysisService,
    build_three_session_momentum,
    dataframe_from_cache_payload,
    dataframe_to_cache_payload,
)
from app.domain.models.market_data import MarketDataBundle, MarketSnapshot


class InMemoryCache:
    def __init__(self):
        self.store = {}
        self.get_calls = []
        self.set_calls = []

    def get(self, key, ttl_sec):
        self.get_calls.append((key, ttl_sec))
        return self.store.get(key)

    def set(self, key, value):
        self.set_calls.append((key, value))
        self.store[key] = value


def _daily_history(rows: int = 70) -> pd.DataFrame:
    index = pd.date_range("2026-01-01", periods=rows, freq="B")
    close = pd.Series([100 + i for i in range(rows)], index=index, dtype=float)
    return pd.DataFrame(
        {
            "Open": close - 1,
            "High": close + 2,
            "Low": close - 3,
            "Close": close,
            "Volume": [1000 + i for i in range(rows)],
        },
        index=index,
    )


def _intraday_history() -> pd.DataFrame:
    prev_date = _daily_history().index[-2].date().isoformat()
    index = pd.to_datetime(
        [
            f"{prev_date} 09:00",
            f"{prev_date} 11:25",
            f"{prev_date} 12:30",
            f"{prev_date} 14:55",
        ]
    )
    return pd.DataFrame(
        {
            "Open": [166.0, 167.0, 167.0, 168.0],
            "High": [168.0, 169.0, 168.0, 169.0],
            "Low": [165.0, 166.0, 166.0, 167.0],
            "Close": [167.0, 168.0, 168.0, 168.0],
            "Volume": [1000.0, 1000.0, 1000.0, 2000.0],
        },
        index=index,
    )


def test_dataframe_cache_payload_roundtrip():
    frame = _daily_history(3)

    restored = dataframe_from_cache_payload(dataframe_to_cache_payload(frame))

    assert restored is not None
    assert list(restored.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert restored.iloc[-1]["Close"] == 102.0


def test_build_analysis_result_fetches_and_caches_histories():
    cache = InMemoryCache()
    calls = {"daily": 0, "intraday": 0}

    def fetch_daily(_code4):
        calls["daily"] += 1
        return _daily_history()

    def fetch_intraday(_code4):
        calls["intraday"] += 1
        return _intraday_history()

    service = TechnicalAnalysisService(
        file_cache=cache,
        fetch_daily_history=fetch_daily,
        fetch_intraday_history=fetch_intraday,
    )

    first = service.build_analysis_result(name="Sample", code4="1234")
    second = service.build_analysis_result(name="Sample", code4="1234")

    assert first.snapshot.price.latest == 169.0
    assert first.intraday_price_timestamp == "2026-04-07 14:55"
    assert first.three_session_momentum.change_pct == pytest.approx((168.0 / 166.0 - 1) * 100)
    assert first.vwap_snapshot["vwap_source"] == "本日5分足"
    assert first.previous_intraday_snapshot["prev_vwap_source"] == "前日5分足"
    assert first.previous_intraday_snapshot["prev_am_vwap_maintained"] is True
    assert first.previous_intraday_snapshot["previous_pm_evaluation"] == "高値維持"
    assert second.snapshot.price.latest == 169.0
    assert calls == {"daily": 1, "intraday": 1}
    assert len(cache.set_calls) == 2


def test_build_analysis_result_falls_back_to_daily_reference_vwap():
    service = TechnicalAnalysisService(
        file_cache=InMemoryCache(),
        fetch_daily_history=lambda _code4: _daily_history(),
        fetch_intraday_history=lambda _code4: pd.DataFrame(),
    )

    result = service.build_analysis_result(name="Sample", code4="1234")

    assert result.vwap_snapshot["vwap_source"] == "日足参考値"
    assert result.vwap_snapshot["latest_bar_time"] == "終値"
    assert result.intraday_price_timestamp == "2026-04-08 終値"
    assert result.previous_intraday_snapshot["previous_pm_evaluation"] == "N/A"


def test_build_analysis_result_from_market_data_bundle():
    bundle = MarketDataBundle(
        code4="1234",
        daily_history=_daily_history(),
        intraday_history=_intraday_history(),
        snapshot=MarketSnapshot(price=169.0),
    )

    result = TechnicalAnalysisService.build_analysis_result_from_bundle(name="Sample", bundle=bundle)

    assert result.name == "Sample"
    assert result.code4 == "1234"
    assert result.snapshot.price.latest == 169.0
    assert result.intraday_price_timestamp == "2026-04-07 14:55"
    assert result.three_session_momentum.sessions[-1].session_date == "2026-04-07"
    assert result.vwap_snapshot["vwap_source"] == "本日5分足"
    assert result.previous_intraday_snapshot["prev_pm_vwap_maintained"] is True


def test_build_three_session_momentum_from_daily_history():
    momentum = build_three_session_momentum(_daily_history())

    assert [session.session_date for session in momentum.sessions] == ["2026-04-03", "2026-04-06", "2026-04-07"]
    assert [session.high_breakout for session in momentum.sessions] == [True, True, True]
    assert [session.low_higher for session in momentum.sessions] == [True, True, True]
    assert momentum.change_pct == pytest.approx((168.0 / 166.0 - 1) * 100)
    assert [session.volume_vs_avg20_pct for session in momentum.sessions] == pytest.approx(
        [
            1066.0 / 1056.5 * 100,
            1067.0 / 1057.5 * 100,
            1068.0 / 1058.5 * 100,
        ]
    )


def test_build_three_session_momentum_returns_none_for_missing_comparison_data():
    momentum = build_three_session_momentum(_daily_history(5))

    assert [session.session_date for session in momentum.sessions] == ["2026-01-02", "2026-01-05", "2026-01-06"]
    assert [session.high_breakout for session in momentum.sessions] == [None, None, True]
    assert [session.low_higher for session in momentum.sessions] == [True, True, True]
    assert [session.volume_vs_avg20_pct for session in momentum.sessions] == [None, None, None]
    assert momentum.change_pct == pytest.approx((103.0 / 101.0 - 1) * 100)
