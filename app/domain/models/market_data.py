"""Domain models for market data fetched from external providers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import pandas as pd


MARKET_SNAPSHOT_KEYS = (
    "price",
    "market_cap",
    "per",
    "pbr",
    "industry",
    "div_yield",
    "payout_ratio",
    "as_of",
)


@dataclass(frozen=True)
class MarketSnapshot:
    price: float | None = None
    market_cap: float | None = None
    per: float | None = None
    pbr: float | None = None
    industry: str | None = None
    div_yield: float | None = None
    payout_ratio: float | None = None
    as_of: str | None = None

    @classmethod
    def empty(cls) -> "MarketSnapshot":
        return cls()

    @classmethod
    def from_mapping(cls, snapshot: Mapping[str, Any]) -> "MarketSnapshot":
        return cls(
            price=snapshot.get("price"),
            market_cap=snapshot.get("market_cap"),
            per=snapshot.get("per"),
            pbr=snapshot.get("pbr"),
            industry=snapshot.get("industry") if isinstance(snapshot.get("industry"), str) else None,
            div_yield=snapshot.get("div_yield"),
            payout_ratio=snapshot.get("payout_ratio"),
            as_of=snapshot.get("as_of") if isinstance(snapshot.get("as_of"), str) else None,
        )

    def to_dict(self) -> dict[str, float | str | None]:
        return {key: getattr(self, key) for key in MARKET_SNAPSHOT_KEYS}

    @property
    def has_price(self) -> bool:
        return self.price is not None


@dataclass(frozen=True)
class MarketDataBundle:
    code4: str
    daily_history: pd.DataFrame
    intraday_history: pd.DataFrame
    snapshot: MarketSnapshot


__all__ = [
    "MARKET_SNAPSHOT_KEYS",
    "MarketDataBundle",
    "MarketSnapshot",
]
