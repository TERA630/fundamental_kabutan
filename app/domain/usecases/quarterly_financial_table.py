"""Domain use-case for building quarterly financial metric rows."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.models.quarterly_financials import QuarterlyActual, QuarterlyMetricRow
from app.domain.policies.quarterly_growth_metrics import assign_quarter, build_quarterly_growth_metrics, resolve_operating_margin


@dataclass(frozen=True)
class BuildQuarterlyFinancialTableUseCase:
    fiscal_end_month: int | None = None
    max_quarters: int = 5

    def execute(self, rows: tuple[QuarterlyActual, ...]) -> tuple[QuarterlyMetricRow, ...]:
        if not rows:
            return ()

        resolved = [self._resolve_quarter_row(row) for row in rows]
        actual_only = [row for row in resolved if row.quarter is not None]
        actual_only.sort(key=lambda r: (r.fiscal_year, _month_order(r.quarter_end_month)))

        latest = actual_only[-self.max_quarters :]
        prior_lookup = {(row.fiscal_year, row.quarter): row for row in actual_only}

        out: list[QuarterlyMetricRow] = []
        for row in latest:
            previous = prior_lookup.get((row.fiscal_year - 1, row.quarter))
            growth = build_quarterly_growth_metrics(previous=previous, current=row)
            operating_margin = resolve_operating_margin(
                row.operating_margin,
                sales=row.sales,
                operating_profit=row.operating_profit if row.operating_profit is not None else row.ordinary_profit,
            )
            out.append(
                QuarterlyMetricRow(
                    fiscal_year=row.fiscal_year,
                    quarter=row.quarter,
                    quarter_end_month=row.quarter_end_month,
                    sales=row.sales,
                    operating_profit=row.operating_profit,
                    ordinary_profit=row.ordinary_profit,
                    final_profit=row.final_profit,
                    revised_eps=row.revised_eps,
                    operating_profit_yoy_pct=growth.operating_profit_yoy.value_pct,
                    revised_eps_yoy_pct=growth.revised_eps_yoy.value_pct,
                    operating_margin_pct=operating_margin,
                    sales_yoy_pct=growth.sales_yoy.value_pct,
                )
            )
        return tuple(out)

    def _resolve_quarter_row(self, row: QuarterlyActual) -> QuarterlyActual:
        if row.quarter is not None:
            return row
        return assign_quarter(row=row, fiscal_end_month=self.fiscal_end_month)


def _month_order(month: int | None) -> int:
    if month is None:
        return 99
    return month


__all__ = ["BuildQuarterlyFinancialTableUseCase"]
