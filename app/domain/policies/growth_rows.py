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


def has_complete_cagr_values(row: KabutanForecastRow) -> bool:
    return row.sales is not None and row.operating_profit is not None and row.revised_eps is not None


def select_cagr_row_by_year(growth_rows: list[KabutanForecastRow]) -> dict[int, KabutanForecastRow]:
    return {row.year: row for row in growth_rows if has_complete_cagr_values(row)}


__all__ = ["build_growth_rows", "has_complete_cagr_values", "select_cagr_row_by_year"]
