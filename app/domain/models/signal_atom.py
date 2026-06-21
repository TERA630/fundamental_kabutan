"""Named, auditable conditions used by composite domain decisions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class SignalAtom:
    """One boolean condition and its conditional score contribution.

    Atoms in the same group can share ``group_max_points`` to cap their combined
    contribution while retaining each underlying reason.
    """

    signal_id: str
    matched: bool
    points: int = 0
    group: str | None = None
    group_max_points: int | None = None

    def __post_init__(self) -> None:
        if not self.signal_id:
            raise ValueError("SignalAtom signal_id must not be empty")
        if self.points < 0:
            raise ValueError("SignalAtom points must not be negative")
        if self.group is None and self.group_max_points is not None:
            raise ValueError("SignalAtom group_max_points requires a group")
        if self.group_max_points is not None and self.group_max_points < 0:
            raise ValueError("SignalAtom group_max_points must not be negative")


def score_signal_atoms(atoms: Iterable[SignalAtom]) -> int:
    """Return active atom points, applying each group's shared cap once."""

    ungrouped_total = 0
    grouped_totals: dict[str, int] = {}
    grouped_caps: dict[str, int | None] = {}

    for atom in atoms:
        if atom.group is None:
            if atom.matched:
                ungrouped_total += atom.points
            continue

        existing_cap = grouped_caps.setdefault(atom.group, atom.group_max_points)
        if existing_cap != atom.group_max_points:
            raise ValueError(f"SignalAtom group '{atom.group}' has inconsistent caps")
        if atom.matched:
            grouped_totals[atom.group] = grouped_totals.get(atom.group, 0) + atom.points

    return ungrouped_total + sum(
        min(points, grouped_caps[group]) if grouped_caps[group] is not None else points
        for group, points in grouped_totals.items()
    )


__all__ = ["SignalAtom", "score_signal_atoms"]
