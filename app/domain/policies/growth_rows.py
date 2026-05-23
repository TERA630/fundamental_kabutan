"""Domain policy for selecting growth comparison rows."""

from __future__ import annotations

from app.domain.models.kabutan_forecast import KabutanForecastRow


def build_growth_rows(rows: list[KabutanForecastRow]) -> list[KabutanForecastRow]:
    """Return rows for growth comparisons, excluding same-year forecast when same-year actual exists."""
    targets: list[KabutanForecastRow] = []
    for row in rows:
        if row.section == "実績":
            targets.append(row)
            continue
        if row.section == "予想":
            if targets and targets[-1].section == "実績" and targets[-1].year == row.year:
                continue
            targets.append(row)
    return targets


__all__ = ["build_growth_rows"]
