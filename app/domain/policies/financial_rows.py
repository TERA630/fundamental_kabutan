"""Domain policy for selecting financial rows for display."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FinancialRowCandidate:
    year: int
    net_income: int | None
    equity: int | None
    operating_profit: int | None
    interest_bearing_debt: int | None
    bps: float | None


def _is_common_year(row: FinancialRowCandidate) -> bool:
    return all(
        value is not None
        for value in (
            row.net_income,
            row.equity,
            row.operating_profit,
            row.interest_bearing_debt,
            row.bps,
        )
    ) and row.bps != 0 and (row.equity + row.interest_bearing_debt) != 0


def select_common_financial_rows(rows: list[FinancialRowCandidate], max_years: int = 3) -> list[FinancialRowCandidate]:
    """Select up to max_years rows starting from latest valid year, preferring common-year completeness."""
    by_year: dict[int, list[FinancialRowCandidate]] = {}
    for row in rows:
        by_year.setdefault(row.year, []).append(row)

    common_rows: list[FinancialRowCandidate] = []
    for year in sorted(by_year.keys(), reverse=True):
        candidates = by_year[year]
        common_candidate = next((row for row in candidates if _is_common_year(row)), None)
        if common_candidate is not None:
            common_rows.append(common_candidate)

    if not common_rows:
        return []

    latest_year = common_rows[0].year
    window_years = {latest_year - offset for offset in range(max_years)}
    selected = [row for row in common_rows if row.year in window_years]
    return sorted(selected, key=lambda row: row.year)


__all__ = [
    "FinancialRowCandidate",
    "select_common_financial_rows",
]
