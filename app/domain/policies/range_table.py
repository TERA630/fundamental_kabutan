"""Typed value-range lookup used by domain scoring policies.

The bands are evaluated from the highest inclusive lower bound to the lowest.
Values below every band, and missing values, resolve to ``default``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar


ResultT = TypeVar("ResultT")


@dataclass(frozen=True)
class RangeBand(Generic[ResultT]):
    """A result for values greater than or equal to ``minimum``."""

    minimum: float
    result: ResultT


@dataclass(frozen=True)
class RangeTable(Generic[ResultT]):
    """Map a numeric value to a result using descending inclusive bands."""

    bands: tuple[RangeBand[ResultT], ...]
    default: ResultT

    def __post_init__(self) -> None:
        minimums = tuple(band.minimum for band in self.bands)
        if minimums != tuple(sorted(minimums, reverse=True)):
            raise ValueError("RangeTable bands must be ordered by descending minimum")

    def resolve(self, value: float | int | None) -> ResultT:
        if value is None:
            return self.default

        numeric_value = float(value)
        for band in self.bands:
            if numeric_value >= band.minimum:
                return band.result
        return self.default
