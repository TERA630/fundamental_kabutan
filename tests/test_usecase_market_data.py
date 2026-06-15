import pandas as pd

from app.domain.models.market_data import MarketSnapshot
from app.domain.usecases.market_data import (
    MARKET_SNAPSHOT_TTL_SEC,
    MarketDataService,
    build_market_snapshot_cache_key,
)


class InMemoryCache:
    def __init__(self):
        self.store = {}
        self.set_calls = []

    def get(self, key, _ttl):
        return self.store.get(key)

    def set(self, key, value):
        self.set_calls.append((key, value))
        self.store[key] = value


def _history(rows: int = 3) -> pd.DataFrame:
    index = pd.date_range("2026-05-29", periods=rows, freq="B")
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


def test_market_data_service_fetches_bundle_and_reuses_cache():
    cache = InMemoryCache()
    calls = {"daily": 0, "intraday": 0, "snapshot": 0}

    def fetch_daily(_code4):
        calls["daily"] += 1
        return _history()

    def fetch_intraday(_code4):
        calls["intraday"] += 1
        return _history(2)

    def fetch_snapshot(_code4, *, daily_history=None):
        calls["snapshot"] += 1
        assert daily_history is not None
        return MarketSnapshot(price=float(daily_history.iloc[-1]["Close"]), market_cap=123_000_000.0)

    service = MarketDataService(
        file_cache=cache,
        fetch_daily_history=fetch_daily,
        fetch_intraday_history=fetch_intraday,
        fetch_market_snapshot=fetch_snapshot,
    )

    first = service.fetch_bundle("7203")
    second = service.fetch_bundle("7203")

    assert first.code4 == "7203"
    assert first.snapshot.price == 102.0
    assert first.snapshot.market_cap == 123_000_000.0
    assert second.snapshot.price == 102.0
    assert calls == {"daily": 1, "intraday": 1, "snapshot": 1}
    assert build_market_snapshot_cache_key("7203") in cache.store
    assert len(cache.set_calls) == 3


def test_market_data_service_does_not_cache_snapshot_without_price():
    cache = InMemoryCache()
    calls = {"snapshot": 0}

    def fetch_snapshot(_code4, *, daily_history=None):
        calls["snapshot"] += 1
        return MarketSnapshot(market_cap=123_000_000.0)

    service = MarketDataService(
        file_cache=cache,
        fetch_daily_history=lambda _code4: _history(),
        fetch_intraday_history=lambda _code4: _history(2),
        fetch_market_snapshot=fetch_snapshot,
    )

    first = service.fetch_market_snapshot_cached("7203", daily_history=_history())
    second = service.fetch_market_snapshot_cached("7203", daily_history=_history())

    assert first == MarketSnapshot.empty()
    assert second == MarketSnapshot.empty()
    assert calls["snapshot"] == 2
    assert build_market_snapshot_cache_key("7203") not in cache.store


def test_market_snapshot_cache_ttl_matches_existing_yfinance_ttl():
    assert MARKET_SNAPSHOT_TTL_SEC == 12 * 60 * 60
