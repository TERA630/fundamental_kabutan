"""Domain use-case: cached market data bundle retrieval."""

from __future__ import annotations

from typing import Any, Mapping, Protocol

import pandas as pd

from app.domain.models.market_data import MarketDataBundle, MarketSnapshot
from app.domain.policies.market_history import (
    TECH_DAILY_HISTORY_TTL_SEC,
    TECH_INTRADAY_HISTORY_TTL_SEC,
    build_technical_daily_history_cache_key,
    build_technical_intraday_history_cache_key,
)
from app.domain.usecases.technical_analysis import dataframe_from_cache_payload, dataframe_to_cache_payload

MARKET_SNAPSHOT_TTL_SEC = 12 * 60 * 60


class MarketDataCachePort(Protocol):
    def get(self, key: str, ttl_sec: int) -> Any: ...

    def set(self, key: str, value: Any) -> None: ...


class DailyHistoryProvider(Protocol):
    def __call__(self, code4: str) -> pd.DataFrame: ...


class IntradayHistoryProvider(Protocol):
    def __call__(self, code4: str) -> pd.DataFrame: ...


class MarketSnapshotProvider(Protocol):
    def __call__(
        self,
        code4: str,
        *,
        daily_history: pd.DataFrame | None = None,
    ) -> MarketSnapshot | Mapping[str, Any]: ...


def build_market_snapshot_cache_key(code4: str) -> str:
    return f"yf_{code4}"


def normalize_market_snapshot_model(snapshot: MarketSnapshot | Mapping[str, Any]) -> MarketSnapshot:
    if isinstance(snapshot, MarketSnapshot):
        return snapshot
    return MarketSnapshot.from_mapping(snapshot)


class MarketDataService:
    """Fetches and caches market histories plus a derived market snapshot."""

    def __init__(
        self,
        file_cache: MarketDataCachePort,
        fetch_daily_history: DailyHistoryProvider | None = None,
        fetch_intraday_history: IntradayHistoryProvider | None = None,
        fetch_market_snapshot: MarketSnapshotProvider | None = None,
    ):
        self.file_cache = file_cache
        if fetch_daily_history is None or fetch_intraday_history is None or fetch_market_snapshot is None:
            raise ValueError("MarketDataService requires market data providers")
        self.fetch_daily_history = fetch_daily_history
        self.fetch_intraday_history = fetch_intraday_history
        self.fetch_market_snapshot = fetch_market_snapshot

    def fetch_bundle(self, code4: str) -> MarketDataBundle:
        daily_history = self.fetch_daily_history_cached(code4)
        intraday_history = self.fetch_intraday_history_cached(code4)
        snapshot = self.fetch_market_snapshot_cached(code4, daily_history=daily_history)
        return MarketDataBundle(
            code4=code4,
            daily_history=daily_history,
            intraday_history=intraday_history,
            snapshot=snapshot,
        )

    def fetch_daily_history_cached(self, code4: str) -> pd.DataFrame:
        key = build_technical_daily_history_cache_key(code4)
        cached = dataframe_from_cache_payload(self.file_cache.get(key, TECH_DAILY_HISTORY_TTL_SEC))
        if cached is not None:
            return cached
        frame = self.fetch_daily_history(code4)
        self.file_cache.set(key, dataframe_to_cache_payload(frame))
        return frame

    def fetch_intraday_history_cached(self, code4: str) -> pd.DataFrame:
        key = build_technical_intraday_history_cache_key(code4)
        cached = dataframe_from_cache_payload(self.file_cache.get(key, TECH_INTRADAY_HISTORY_TTL_SEC))
        if cached is not None:
            return cached
        frame = self.fetch_intraday_history(code4)
        self.file_cache.set(key, dataframe_to_cache_payload(frame))
        return frame

    def fetch_market_snapshot_cached(self, code4: str, *, daily_history: pd.DataFrame | None = None) -> MarketSnapshot:
        key = build_market_snapshot_cache_key(code4)
        cached = self.file_cache.get(key, MARKET_SNAPSHOT_TTL_SEC)
        if isinstance(cached, MarketSnapshot):
            return cached
        if isinstance(cached, Mapping):
            return MarketSnapshot.from_mapping(cached)

        snapshot = normalize_market_snapshot_model(self.fetch_market_snapshot(code4, daily_history=daily_history))
        if snapshot.has_price:
            self.file_cache.set(key, snapshot.to_dict())
            return snapshot
        return MarketSnapshot.empty()


__all__ = [
    "MARKET_SNAPSHOT_TTL_SEC",
    "MarketDataCachePort",
    "MarketDataService",
    "build_market_snapshot_cache_key",
    "normalize_market_snapshot_model",
]
