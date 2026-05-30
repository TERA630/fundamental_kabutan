import pandas as pd

from app.domain.usecases.technical_analysis import (
    TechnicalAnalysisService,
    dataframe_from_cache_payload,
    dataframe_to_cache_payload,
)


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
    index = pd.date_range("2026-05-29 09:00", periods=2, freq="5min")
    return pd.DataFrame(
        {
            "Open": [168.0, 169.0],
            "High": [170.0, 171.0],
            "Low": [167.0, 168.0],
            "Close": [169.0, 170.0],
            "Volume": [1000.0, 2000.0],
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
    assert first.vwap_snapshot["vwap_source"] == "本日5分足"
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
