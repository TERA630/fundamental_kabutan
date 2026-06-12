import pandas as pd
import pytest

from app.data import market_data_provider as provider


def _history() -> pd.DataFrame:
    index = pd.date_range("2026-05-29 09:00", periods=3, freq="5min")
    return pd.DataFrame(
        {
            "Open": [100.0, 101.0, 102.0],
            "High": [102.0, 103.0, 104.0],
            "Low": [99.0, 100.0, 101.0],
            "Close": [101.0, 102.0, 103.0],
            "Volume": [1000.0, 0.0, 2000.0],
        },
        index=index,
    )


def test_technical_cache_keys_and_ttls():
    assert provider.TECH_DAILY_HISTORY_TTL_SEC == 12 * 60 * 60
    assert provider.TECH_INTRADAY_HISTORY_TTL_SEC == 5 * 60
    assert provider.build_technical_daily_history_cache_key("7203") == "tech_daily_7203_4mo_1d"
    assert provider.build_technical_intraday_history_cache_key("7203") == "tech_intraday_7203_5m_jst"


def test_fetch_yfinance_daily_history_uses_ticker_history(monkeypatch):
    class FakeTicker:
        def __init__(self, symbol):
            self.symbol = symbol

        def history(self, *, period, interval, auto_adjust):
            assert self.symbol == "7203.T"
            assert period == "4mo"
            assert interval == "1d"
            assert auto_adjust is False
            return _history()

    class FakeYf:
        Ticker = FakeTicker

    monkeypatch.setattr(provider, "yf", FakeYf)

    out = provider.fetch_yfinance_daily_history("7203")

    assert list(out.columns) == list(provider.TECH_DAILY_COLUMNS)
    assert len(out) == 3
    assert out.iloc[-1]["Close"] == 103.0


def test_fetch_yfinance_intraday_history_normalizes_download_multiindex(monkeypatch):
    base = _history()
    multi = pd.concat({"7203.T": base}, axis=1).swaplevel(0, 1, axis=1)

    class FakeYf:
        @staticmethod
        def download(symbol, *, period, interval, auto_adjust, progress):
            assert symbol == "7203.T"
            assert period == "5d"
            assert interval == "5m"
            assert auto_adjust is False
            assert progress is False
            return multi

    monkeypatch.setattr(provider, "yf", FakeYf)

    out = provider.fetch_yfinance_intraday_history("7203")

    assert list(out.columns) == list(provider.TECH_DAILY_COLUMNS)
    assert len(out) == 3


def test_fetch_yfinance_intraday_history_converts_utc_index_to_jst(monkeypatch):
    base = _history()
    base.index = pd.date_range("2026-05-29 00:00", periods=3, freq="5min", tz="UTC")

    class FakeYf:
        @staticmethod
        def download(symbol, *, period, interval, auto_adjust, progress):
            return base

    monkeypatch.setattr(provider, "yf", FakeYf)

    out = provider.fetch_yfinance_intraday_history("7203")

    assert out.index[0] == pd.Timestamp("2026-05-29 09:00")
    assert out.index.tz is None


def test_build_market_snapshot_from_daily_history_uses_latest_close():
    snapshot = provider.build_market_snapshot_from_daily_history(_history())

    assert snapshot.price == 103.0
    assert snapshot.as_of == "2026-05-29 終値"


def test_fetch_yfinance_market_snapshot_reuses_daily_history_without_history_call(monkeypatch):
    class FakeTicker:
        def __init__(self, symbol):
            self.symbol = symbol
            self.fast_info = {"market_cap": 123_000_000.0}
            self.info = {"trailingPE": 12.5, "priceToBook": 1.2, "sector": "輸送用機器"}

        def history(self, **_kwargs):
            raise AssertionError("daily_history should be reused")

    class FakeYf:
        Ticker = FakeTicker

    monkeypatch.setattr(provider, "yf", FakeYf)

    snapshot = provider.fetch_yfinance_market_snapshot("7203", daily_history=_history())

    assert snapshot.price == 103.0
    assert snapshot.market_cap == 123_000_000.0
    assert snapshot.per == 12.5
    assert snapshot.pbr == 1.2
    assert snapshot.industry == "輸送用機器"


def test_fetch_yfinance_analyst_estimates_reads_year_revision_30day_rows(monkeypatch):
    eps_revisions = pd.DataFrame(
        {
            "upLast30days": [3, 4],
            "downLast30days": [7, 8],
        },
        index=["0y", "+1y"],
    )

    class FakeTicker:
        def __init__(self, symbol):
            self.symbol = symbol
            self.info = {"targetMeanPrice": 2500.0, "numberOfAnalystOpinions": 9}
            self.eps_revisions = eps_revisions

    class FakeYf:
        Ticker = FakeTicker

    monkeypatch.setattr(provider, "yf", FakeYf)

    estimates = provider.fetch_yfinance_analyst_estimates("7203")

    assert estimates.target_mean_price == 2500.0
    assert estimates.number_of_analyst_opinions == 9
    assert estimates.current_year_eps_revisions.up_last_30_days == 3
    assert estimates.current_year_eps_revisions.down_last_30_days == 7
    assert estimates.next_year_eps_revisions.up_last_30_days == 4
    assert estimates.next_year_eps_revisions.down_last_30_days == 8


def test_build_intraday_vwap_snapshot_filters_zero_volume():
    snapshot = provider.build_intraday_vwap_snapshot(_history())

    typical_1 = (102 + 99 + 101) / 3
    typical_3 = (104 + 101 + 103) / 3
    expected_vwap = ((typical_1 * 1000) + (typical_3 * 2000)) / 3000
    assert snapshot["latest"] == 103.0
    assert snapshot["open"] == 100.0
    assert snapshot["high"] == 104.0
    assert snapshot["low"] == 99.0
    assert snapshot["volume"] == 3000.0
    assert snapshot["vwap"] == expected_vwap
    assert snapshot["latest_bar_time"] == "09:10"
    assert snapshot["latest_price_source"] == "intraday_5m"
    assert snapshot["latest_price_timestamp"] == "2026-05-29 09:10"
    assert snapshot["vwap_source"] == "本日5分足"
    assert snapshot["vwap_timestamp"] == "2026-05-29 09:10"
    assert snapshot["current_am_vwap"] == pytest.approx(expected_vwap)
    assert snapshot["current_pm_vwap"] is None
    assert snapshot["current_intraday_session"] == "前場"


def test_build_intraday_vwap_snapshot_uses_latest_session_only():
    intraday = pd.DataFrame(
        {
            "Open": [80.0, 90.0, 100.0, 101.0],
            "High": [81.0, 91.0, 102.0, 103.0],
            "Low": [79.0, 89.0, 99.0, 100.0],
            "Close": [80.0, 90.0, 101.0, 102.0],
            "Volume": [10_000.0, 10_000.0, 1000.0, 2000.0],
        },
        index=pd.to_datetime(
            [
                "2026-05-28 14:50",
                "2026-05-28 14:55",
                "2026-05-29 09:00",
                "2026-05-29 09:05",
            ]
        ),
    )

    snapshot = provider.build_intraday_vwap_snapshot(intraday)
    typical_1 = (102.0 + 99.0 + 101.0) / 3
    typical_2 = (103.0 + 100.0 + 102.0) / 3
    expected_vwap = ((typical_1 * 1000.0) + (typical_2 * 2000.0)) / 3000.0

    assert snapshot["open"] == 100.0
    assert snapshot["volume"] == 3000.0
    assert snapshot["vwap"] == pytest.approx(expected_vwap)
    assert snapshot["latest_price_timestamp"] == "2026-05-29 09:05"


def test_build_intraday_vwap_snapshot_splits_current_am_and_pm_vwap():
    intraday = pd.DataFrame(
        {
            "Open": [100.0, 101.0, 102.0, 103.0],
            "High": [102.0, 103.0, 104.0, 105.0],
            "Low": [99.0, 100.0, 101.0, 102.0],
            "Close": [101.0, 102.0, 103.0, 104.0],
            "Volume": [1000.0, 2000.0, 1000.0, 3000.0],
        },
        index=pd.to_datetime(["2026-05-29 09:00", "2026-05-29 11:25", "2026-05-29 12:30", "2026-05-29 14:55"]),
    )

    snapshot = provider.build_intraday_vwap_snapshot(intraday)
    typical_1 = (102.0 + 99.0 + 101.0) / 3
    typical_2 = (103.0 + 100.0 + 102.0) / 3
    typical_3 = (104.0 + 101.0 + 103.0) / 3
    typical_4 = (105.0 + 102.0 + 104.0) / 3
    expected_am_vwap = ((typical_1 * 1000.0) + (typical_2 * 2000.0)) / 3000.0
    expected_pm_vwap = ((typical_3 * 1000.0) + (typical_4 * 3000.0)) / 4000.0

    assert snapshot["current_am_vwap"] == pytest.approx(expected_am_vwap)
    assert snapshot["current_pm_vwap"] == pytest.approx(expected_pm_vwap)
    assert snapshot["current_intraday_session"] == "後場"


def test_build_previous_session_intraday_snapshot():
    daily = pd.DataFrame(
        {
            "Open": [100.0, 105.0],
            "High": [105.0, 106.0],
            "Low": [99.0, 103.0],
            "Close": [104.0, 105.0],
            "Volume": [1000.0, 1200.0],
        },
        index=pd.to_datetime(["2026-05-28", "2026-05-29"]),
    )
    intraday = pd.DataFrame(
        {
            "Open": [100.0, 101.0, 102.0, 102.0],
            "High": [102.0, 103.0, 103.0, 105.0],
            "Low": [99.0, 100.0, 101.0, 101.0],
            "Close": [101.0, 102.0, 102.0, 104.0],
            "Volume": [1000.0, 2000.0, 1000.0, 3000.0],
        },
        index=pd.to_datetime(["2026-05-28 09:00", "2026-05-28 11:25", "2026-05-28 12:30", "2026-05-28 14:55"]),
    )

    snapshot = provider.build_previous_session_intraday_snapshot(daily, intraday)
    typical_1 = (102.0 + 99.0 + 101.0) / 3
    typical_2 = (103.0 + 100.0 + 102.0) / 3
    typical_3 = (103.0 + 101.0 + 102.0) / 3
    typical_4 = (105.0 + 101.0 + 104.0) / 3
    expected_prev_vwap = ((typical_1 * 1000.0) + (typical_2 * 2000.0) + (typical_3 * 1000.0) + (typical_4 * 3000.0)) / 7000.0
    expected_am_vwap = ((typical_1 * 1000.0) + (typical_2 * 2000.0)) / 3000.0
    expected_pm_vwap = ((typical_3 * 1000.0) + (typical_4 * 3000.0)) / 4000.0

    assert snapshot["prev_vwap_source"] == "前日5分足"
    assert snapshot["prev_vwap"] == pytest.approx(expected_prev_vwap)
    assert snapshot["prev_am_vwap"] == pytest.approx(expected_am_vwap)
    assert snapshot["prev_pm_vwap"] == pytest.approx(expected_pm_vwap)
    assert snapshot["prev_am_vwap_maintained"] is True
    assert snapshot["prev_pm_vwap_maintained"] is True
    assert snapshot["previous_pm_vwap_position"] == "上"
    assert snapshot["previous_pm_evaluation"] == "後場上昇"
    assert snapshot["pm_open"] == 102.0
    assert snapshot["pm_high"] == 105.0
    assert snapshot["pm_low"] == 101.0
    assert snapshot["pm_return_pct"] == pytest.approx((104.0 / 102.0 - 1) * 100)
    assert snapshot["pm_close_position"] == pytest.approx(0.75)


def test_build_previous_session_intraday_snapshot_returns_na_when_previous_bars_missing():
    daily = pd.DataFrame(
        {
            "Open": [100.0, 105.0],
            "High": [105.0, 106.0],
            "Low": [99.0, 103.0],
            "Close": [104.0, 105.0],
            "Volume": [1000.0, 1200.0],
        },
        index=pd.to_datetime(["2026-05-28", "2026-05-29"]),
    )

    snapshot = provider.build_previous_session_intraday_snapshot(daily, pd.DataFrame())

    assert snapshot["prev_vwap"] is None
    assert snapshot["previous_pm_vwap_position"] == "N/A"
    assert snapshot["previous_pm_evaluation"] == "N/A"


def test_build_daily_reference_vwap_snapshot():
    daily = pd.DataFrame(
        {
            "Open": [100.0],
            "High": [110.0],
            "Low": [90.0],
            "Close": [105.0],
            "Volume": [1234.0],
        },
        index=pd.to_datetime(["2026-05-29"]),
    )

    snapshot = provider.build_daily_reference_vwap_snapshot(daily)

    assert snapshot["latest"] == 105.0
    assert snapshot["vwap"] == (110 + 90 + 105) / 3
    assert snapshot["latest_bar_time"] == "終値"
    assert snapshot["latest_price_source"] == "daily_close"
    assert snapshot["latest_price_timestamp"] == "2026-05-29 終値"
    assert snapshot["vwap_source"] == "日足参考値"
    assert snapshot["vwap_timestamp"] == "2026-05-29 終値"
    assert snapshot["current_am_vwap"] is None
    assert snapshot["current_pm_vwap"] is None
    assert snapshot["current_intraday_session"] is None


def test_fetch_yfinance_vwap_snapshot_falls_back_to_daily_reference(monkeypatch):
    daily = pd.DataFrame(
        {
            "Open": [100.0],
            "High": [110.0],
            "Low": [90.0],
            "Close": [105.0],
            "Volume": [1234.0],
        },
        index=pd.to_datetime(["2026-05-29"]),
    )

    monkeypatch.setattr(provider, "fetch_yfinance_intraday_history", lambda code4, interval="5m": pd.DataFrame())

    snapshot = provider.fetch_yfinance_vwap_snapshot("7203", daily_history=daily)

    assert snapshot["vwap_source"] == "日足参考値"
    assert snapshot["vwap"] == (110 + 90 + 105) / 3
