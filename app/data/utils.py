"""Data-layer utility helpers."""

from __future__ import annotations

import math
from typing import Any


def safe_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip().replace(",", "")
        if value in ("", "-", "None", "null", "NaN"):
            return None
    try:
        v = float(value)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except Exception:
        return None


__all__ = ["safe_float"]
