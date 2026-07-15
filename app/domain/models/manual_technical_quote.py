"""Domain model for a manually supplied current technical quote."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import isfinite


@dataclass(frozen=True)
class ManualTechnicalQuote:
    """Four current-session values supplied from an external stock application."""

    latest: float
    high: float
    low: float
    vwap: float
    observed_at: datetime

    def __post_init__(self) -> None:
        values = {
            "当日現在値": self.latest,
            "当日高値": self.high,
            "当日安値": self.low,
            "当日VWAP": self.vwap,
        }
        for label, value in values.items():
            if not isfinite(value) or value <= 0:
                raise ValueError(f"{label}は0より大きい数値を入力してください。")
        if self.low > self.high:
            raise ValueError("当日安値は当日高値以下にしてください。")
        if not self.low <= self.latest <= self.high:
            raise ValueError("当日現在値は当日安値から当日高値の範囲内にしてください。")
        if not self.low <= self.vwap <= self.high:
            raise ValueError("当日VWAPは当日安値から当日高値の範囲内にしてください。")


__all__ = ["ManualTechnicalQuote"]
