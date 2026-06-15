"""Domain policy for selecting Kabutan forecast snapshot rows."""

from __future__ import annotations

from app.domain.models.kabutan_forecast import KabutanForecastRow, KabutanForecastSnapshot


def build_kabutan_forecast_snapshot(
    rows: list[KabutanForecastRow],
    base_year: int,
) -> KabutanForecastSnapshot:
    has_current_year_actual = any(
        row.section == "実績" and row.year == base_year for row in rows
    )
    if has_current_year_actual:
        actual_years = {base_year - 2, base_year - 1, base_year}
        forecast_years = {base_year + 1}
    else:
        actual_years = {base_year - 2, base_year - 1}
        forecast_years = {base_year, base_year + 1}

    actual_rows = tuple(
        row for row in rows if row.section == "実績" and row.year in actual_years
    )
    forecast_rows = tuple(
        row for row in rows if row.section == "予想" and row.year in forecast_years
    )
    return KabutanForecastSnapshot(actual_rows=actual_rows, forecast_rows=forecast_rows)


__all__ = ["build_kabutan_forecast_snapshot"]
