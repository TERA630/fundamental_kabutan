"""Build presentation DTOs for the fundamental-analysis view."""

from __future__ import annotations

from typing import Any

from app.domain.models.analyst_estimates import AnalystEstimates
from app.domain.models.display_sections import (
    AnalystEstimatesSection,
    DisplaySections,
    SummarySection,
    ValuationTableSection,
)
from app.domain.models.financial_snapshot import FinancialMetricInputRow
from app.domain.models.kabutan_cashflow import KabutanCashflowRow
from app.domain.models.kabutan_forecast import KabutanForecastPair, KabutanForecastRow
from app.domain.policies.financial_metrics import calc_pbr, calc_roe, calc_roic_approx


def _first_present(data: dict[str, Any] | None, keys: tuple[str, ...]) -> Any:
    if not data:
        return None
    return next((data[key] for key in keys if data.get(key) not in (None, "")), None)


def _fmt_num(value: float | None, digits: int = 2) -> str:
    return "N/A" if value is None else f"{value:,.{digits}f}"


def _fmt_pct(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2f}%"


def _calc_per(price: float | None, eps: float | None) -> float | None:
    return None if price in (None, 0) or eps in (None, 0) else price / eps


def _calc_dividend_yield(price: float | None, dividend: float | None) -> float | None:
    return None if price in (None, 0) or dividend is None else dividend / price * 100


def _calc_fcf_yield(row: KabutanCashflowRow, market_cap: float | None) -> float | None:
    free_cf = row.free_cf
    if free_cf is None and row.operating_cf is not None and row.investing_cf is not None:
        free_cf = row.operating_cf + row.investing_cf
    if free_cf is None or market_cap in (None, 0):
        return None
    return free_cf * 1_000_000 / market_cap * 100


def _forecast_rows(pair: KabutanForecastPair | None) -> list[KabutanForecastRow]:
    if pair is None:
        return []
    if pair.all_rows:
        return list(pair.all_rows)
    return [
        row
        for row in (
            pair.previous2_actual,
            pair.previous_actual,
            pair.current_actual,
            pair.current_forecast,
            pair.next_forecast,
        )
        if row is not None
    ]


def _display_rows(rows: list[KabutanForecastRow], metric: str) -> list[KabutanForecastRow]:
    available = [
        row
        for row in rows
        if (row.revised_eps if metric == "per" else row.dividend) is not None
    ]
    if not available:
        return []
    latest_year = max(row.year for row in available)
    selected: list[KabutanForecastRow] = []
    for year in range(latest_year - 2, latest_year + 1):
        same_year = [row for row in available if row.year == year]
        if same_year:
            selected.append(next((row for row in same_year if row.section == "予想"), same_year[0]))
    return selected


def _year_label(row: KabutanForecastRow) -> str:
    return f"{row.year}年({'予' if row.section == '予想' else '実績'})"


def _actual_year_label(year: int) -> str:
    return f"{year}年(実績)"


def _align(labels: list[str], values: dict[str, str]) -> list[str]:
    return [values.get(label, "N/A") for label in labels] if labels else ["N/A"]


def _label_year(label: str) -> int:
    try:
        return int(label[:4])
    except ValueError:
        return 0


def build_fundamental_output_sections(
    *,
    name: str,
    code4: str,
    master: dict[str, Any] | None,
    price: float | None,
    market_cap: float | None,
    market_snapshot: dict[str, Any] | None = None,
    analyst_estimates: AnalystEstimates | None = None,
    kabutan_forecast_pair: KabutanForecastPair | None = None,
    kabutan_cashflow_rows: tuple[KabutanCashflowRow, ...] = (),
    financial_metric_rows: tuple[FinancialMetricInputRow, ...] = (),
) -> DisplaySections:
    """Translate analysis data into display sections for text renderers."""
    snapshot = market_snapshot or {}
    company_name = str(_first_present(master, ("CompanyName", "Name", "LocalCodeName")) or name)
    industry = str(
        snapshot.get("industry")
        or _first_present(master, ("S33Nm", "Sector33CodeName", "Sector33Name"))
        or "N/A"
    )

    rows = _forecast_rows(kabutan_forecast_pair)
    per_values = {
        _year_label(row): f"{_fmt_num(_calc_per(price, row.revised_eps), 1)}倍"
        for row in _display_rows(rows, "per")
    }
    dividend_values = {
        _year_label(row): _fmt_pct(_calc_dividend_yield(price, row.dividend))
        for row in _display_rows(rows, "dividend")
    }
    market_per = snapshot.get("per")
    if not per_values and isinstance(market_per, (int, float)) and market_per > 0:
        per_values["市場PER"] = f"{float(market_per):.1f}倍"

    pbr_values: dict[str, str] = {}
    roe_values: dict[str, str] = {}
    roic_values: dict[str, str] = {}
    for row in financial_metric_rows:
        label = _actual_year_label(row.year)
        pbr_values[label] = f"{_fmt_num(calc_pbr(row.price, row.bps), 2)}倍"
        roe_values[label] = _fmt_pct(calc_roe(row.net_income, row.equity))
        roic_values[label] = _fmt_pct(
            calc_roic_approx(row.operating_profit, row.equity, row.interest_bearing_debt)
        )

    fcf_values = {
        _actual_year_label(row.year): _fmt_pct(_calc_fcf_yield(row, market_cap))
        for row in kabutan_cashflow_rows
    }
    labels = sorted(
        set(per_values) | set(dividend_values) | set(pbr_values) | set(roe_values) | set(roic_values) | set(fcf_values),
        key=lambda label: (_label_year(label), label),
    )

    return DisplaySections(
        sections=[
            SummarySection(
                company_name=company_name,
                code4=code4,
                price=price,
                market_cap=market_cap,
                industry=industry,
                pbr=snapshot.get("pbr"),
                roe=snapshot.get("roe"),
            ),
            ValuationTableSection(
                year_labels=labels,
                per_values=_align(labels, per_values),
                dividend_values=_align(labels, dividend_values),
                pbr_values=_align(labels, pbr_values) if pbr_values else None,
                roe_values=_align(labels, roe_values) if roe_values else None,
                roic_values=_align(labels, roic_values) if roic_values else None,
                fcf_yield_values=_align(labels, fcf_values) if fcf_values else None,
            ),
            AnalystEstimatesSection(analyst_estimates or AnalystEstimates.empty(), price=price),
        ]
    )


__all__ = ["build_fundamental_output_sections"]
