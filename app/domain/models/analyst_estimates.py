"""Domain models for yFinance analyst estimates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class EpsRevisionPeriod:
    up_last_30_days: int | None = None
    down_last_30_days: int | None = None

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | None) -> "EpsRevisionPeriod":
        value = value or {}
        return cls(
            up_last_30_days=value.get("up_last_30_days"),
            down_last_30_days=value.get("down_last_30_days"),
        )

    def to_dict(self) -> dict[str, int | None]:
        return {
            "up_last_30_days": self.up_last_30_days,
            "down_last_30_days": self.down_last_30_days,
        }


@dataclass(frozen=True)
class AnalystEstimates:
    target_mean_price: float | None = None
    number_of_analyst_opinions: int | None = None
    current_year_eps_revisions: EpsRevisionPeriod = EpsRevisionPeriod()
    next_year_eps_revisions: EpsRevisionPeriod = EpsRevisionPeriod()

    @classmethod
    def empty(cls) -> "AnalystEstimates":
        return cls()

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "AnalystEstimates":
        return cls(
            target_mean_price=value.get("target_mean_price"),
            number_of_analyst_opinions=value.get("number_of_analyst_opinions"),
            current_year_eps_revisions=EpsRevisionPeriod.from_mapping(_as_mapping(value.get("current_year_eps_revisions"))),
            next_year_eps_revisions=EpsRevisionPeriod.from_mapping(_as_mapping(value.get("next_year_eps_revisions"))),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "target_mean_price": self.target_mean_price,
            "number_of_analyst_opinions": self.number_of_analyst_opinions,
            "current_year_eps_revisions": self.current_year_eps_revisions.to_dict(),
            "next_year_eps_revisions": self.next_year_eps_revisions.to_dict(),
        }


def _as_mapping(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


__all__ = [
    "AnalystEstimates",
    "EpsRevisionPeriod",
]
