"""Domain models for watchlist entries."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WatchlistEntry:
    name: str
    code4: str
    sectors: tuple[str, ...] = ()

    def as_tuple(self) -> tuple[str, str]:
        return self.name, self.code4


__all__ = ["WatchlistEntry"]
