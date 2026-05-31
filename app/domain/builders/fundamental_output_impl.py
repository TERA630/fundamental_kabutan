"""Domain output implementation without legacy module dependency."""

from __future__ import annotations

from typing import Any
from app.domain.models.financial_snapshot import FinancialMetricInputRow
from app.domain.models.kabutan_cashflow import KabutanCashflowRow
from app.domain.models.kabutan_forecast import KabutanForecastPair, KabutanForecastRow
from app.domain.builders.analyst_estimates_output import build_analyst_estimates_lines
from app.domain.models.analyst_estimates import AnalystEstimates
from app.domain.models.display_sections import AnalystEstimatesSection, SummarySection, ValuationTableSection, DisplaySections
from app.domain.policies.financial_metrics import calc_pbr, calc_roe, calc_roic_approx



def _first_present(data: dict[str, Any] | None, keys: list[str]) -> Any:
    if not data:
        return None
    for key in keys:
        if key in data and data[key] not in (None, ""):
            return data[key]
    return None


def _fmt_num(v: float | None, digits: int = 2) -> str:
    return "N/A" if v is None else f"{v:,.{digits}f}"


def _fmt_plain_pct(v: float | None) -> str:
    return "N/A" if v is None else f"{v:.2f}%"


def _fmt_money(v: float | None) -> str:
    return "N/A" if v is None else f"{v / 100_000_000:,.1f}億円"


def _build_market_cap_rank(v: float | None) -> str:
    if v is None:
        return "N/A"
    oku = v / 100_000_000
    if oku >= 100_000:
        return "超大型"
    if oku >= 10_000:
        return "大型主役"
    if oku >= 3_000:
        return "中型主役"
    if oku >= 1_000:
        return "小〜中型"
    return "小型"


def calc_per_times(price: float | None, eps: float | None) -> float | None:
    if price in (None, 0) or eps in (None, 0):
        return None
    return price / eps


def calc_dividend_yield_pct(price: float | None, dividend: float | None) -> float | None:
    if price in (None, 0) or dividend is None:
        return None
    return dividend / price * 100


def _resolve_fcf_million_yen(row: KabutanCashflowRow) -> int | None:
    if row.free_cf is not None:
        return row.free_cf
    if row.operating_cf is None or row.investing_cf is None:
        return None
    return row.operating_cf + row.investing_cf


def _calc_fcf_yield_pct(free_cf_million_yen: int | None, market_cap_yen: float | None) -> float | None:
    if free_cf_million_yen is None or market_cap_yen in (None, 0):
        return None
    return ((free_cf_million_yen * 1_000_000) / market_cap_yen) * 100


def fetch_kabutan_rows(pair: KabutanForecastPair | None) -> list[KabutanForecastRow]:
    if pair is None:
        return []
    if pair.all_rows:
        return list(pair.all_rows)
    return [row for row in (pair.previous2_actual, pair.previous_actual, pair.current_actual, pair.current_forecast, pair.next_forecast) if row is not None]


def fetch_display_rows_for_indicator(rows: list[KabutanForecastRow], *, metric: str) -> list[KabutanForecastRow]:
    if metric == "per":
        metric_rows = [row for row in rows if row.revised_eps is not None]
    else:
        metric_rows = [row for row in rows if row.dividend is not None]
    if not metric_rows:
        return []
    latest_year = max(row.year for row in metric_rows)
    target_years = [latest_year - 2, latest_year - 1, latest_year]
    row_by_year: dict[int, KabutanForecastRow] = {}
    for year in target_years:
        year_rows = [row for row in metric_rows if row.year == year]
        if not year_rows:
            continue
        forecast_row = next((row for row in year_rows if row.section == "予想"), None)
        row_by_year[year] = forecast_row or year_rows[0]
    return [row_by_year[year] for year in target_years if year in row_by_year]


def build_year_label(row: KabutanForecastRow) -> str:
    suffix = "(予)" if row.section == "予想" else "(実績)"
    return f"{row.year}年{suffix}"


def build_actual_year_label(year: int) -> str:
    return f"{year}年(実績)"


def _fmt_market_per(value: Any) -> str | None:
    if not isinstance(value, (int, float)):
        return None
    if value <= 0:
        return None
    return f"{float(value):.1f}倍"


def _align_values(year_labels: list[str], values_by_label: dict[str, str]) -> list[str]:
    if not year_labels:
        return ["N/A"]
    return [values_by_label.get(label, "N/A") for label in year_labels]


def _label_year(label: str) -> int:
    try:
        return int(label[:4])
    except ValueError:
        return 0


def build_fundamental_output_sections_impl(
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
    company_name = str(_first_present(master, ["CompanyName", "Name", "LocalCodeName"]) or name)
    industry_name = str((market_snapshot or {}).get("industry") or _first_present(master, ["S33Nm", "Sector33CodeName", "Sector33Name"]) or "N/A")

    all_rows = fetch_kabutan_rows(kabutan_forecast_pair)
    per_rows = fetch_display_rows_for_indicator(all_rows, metric="per")
    dividend_rows = fetch_display_rows_for_indicator(all_rows, metric="dividend")
    per_by_label = {build_year_label(row): f"{_fmt_num(calc_per_times(price, row.revised_eps),1)}倍" for row in per_rows}
    dividend_by_label = {build_year_label(row): _fmt_plain_pct(calc_dividend_yield_pct(price, row.dividend)) for row in dividend_rows}
    market_per = _fmt_market_per((market_snapshot or {}).get("per"))
    if not per_by_label and market_per is not None:
        per_by_label = {"市場PER": market_per}

    pbr_by_label: dict[str, str] = {}
    roe_by_label: dict[str, str] = {}
    roic_by_label: dict[str, str] = {}
    for row in financial_metric_rows:
        label = build_actual_year_label(row.year)
        pbr_by_label[label] = f"{_fmt_num(calc_pbr(row.price, row.bps), 2)}倍"
        roe_by_label[label] = _fmt_plain_pct(calc_roe(row.net_income, row.equity))
        roic_by_label[label] = _fmt_plain_pct(calc_roic_approx(row.operating_profit, row.equity, row.interest_bearing_debt))

    fcf_yield_by_label: dict[str, str] = {}
    for row in kabutan_cashflow_rows:
        fcf_yield_by_label[build_actual_year_label(row.year)] = _fmt_plain_pct(_calc_fcf_yield_pct(_resolve_fcf_million_yen(row), market_cap))

    labels = set(per_by_label) | set(dividend_by_label) | set(pbr_by_label) | set(roe_by_label) | set(roic_by_label) | set(fcf_yield_by_label)
    year_labels = sorted(labels, key=lambda label: (_label_year(label), label))

    per_values = _align_values(year_labels, per_by_label)
    dividend_values = _align_values(year_labels, dividend_by_label)
    pbr_values = _align_values(year_labels, pbr_by_label) if pbr_by_label else None
    roe_values = _align_values(year_labels, roe_by_label) if roe_by_label else None
    roic_values = _align_values(year_labels, roic_by_label) if roic_by_label else None
    fcf_yield_values = _align_values(year_labels, fcf_yield_by_label) if fcf_yield_by_label else None

    summary = SummarySection(
        company_name=company_name,
        code4=code4,
        price=price,
        market_cap=market_cap,
        industry=industry_name,
        pbr=(market_snapshot or {}).get("pbr"),
        roe=(market_snapshot or {}).get("roe"),
    )
    valuation = ValuationTableSection(
        year_labels=year_labels,
        per_values=per_values,
        dividend_values=dividend_values,
        pbr_values=pbr_values,
        roe_values=roe_values,
        roic_values=roic_values,
        fcf_yield_values=fcf_yield_values,
    )
    return DisplaySections(sections=[summary, valuation, AnalystEstimatesSection(analyst_estimates or AnalystEstimates.empty(), price=price)])




def build_indicator_lines(
    *,
    price: float | None,
    market_cap: float | None,
    industry: str,
    pbr: float | None,
    roe: float | None,
) -> list[str]:
    return [
        f"株価：{_fmt_num(price,0)}円",
        f"時価総額：{_fmt_money(market_cap)}({_build_market_cap_rank(market_cap)})",
    ]


def _build_valuation_lines(per_lines: list[str], dividend_lines: list[str]) -> list[str]:
    year_labels: list[str] = []
    if per_lines:
        year_labels = [part.split(" ", 1)[0] for part in per_lines]
    elif dividend_lines:
        year_labels = [part.split(" ", 1)[0] for part in dividend_lines]

    header = "年度|" + "|".join(year_labels) if year_labels else "年度|N/A"
    per_values = [part.split(" ", 1)[1] for part in per_lines] if per_lines else ["N/A"]
    dividend_values = [part.split(" ", 1)[1] for part in dividend_lines] if dividend_lines else ["N/A"]

    return [
        "",
        "■バリュエーション",
        header,
        f"PER|{'|'.join(per_values)}",
        f"配当利回り|{'|'.join(dividend_values)}",
    ]


def build_fundamental_output_text_impl(*, name: str, code4: str, master: dict[str, Any] | None, price: float | None, market_cap: float | None, market_snapshot: dict[str, Any] | None = None, analyst_estimates: AnalystEstimates | None = None, kabutan_forecast_pair: KabutanForecastPair | None = None) -> str:
    company_name = str(_first_present(master, ["CompanyName", "Name", "LocalCodeName"]) or name)
    industry_name = str((market_snapshot or {}).get("industry") or _first_present(master, ["S33Nm", "Sector33CodeName", "Sector33Name"]) or "N/A")

    all_rows = fetch_kabutan_rows(kabutan_forecast_pair)
    per_rows = fetch_display_rows_for_indicator(all_rows, metric="per")
    dividend_rows = fetch_display_rows_for_indicator(all_rows, metric="dividend")
    per_lines = [f"{build_year_label(row)} {_fmt_num(calc_per_times(price, row.revised_eps),1)}倍" for row in per_rows]
    dividend_lines = [f"{build_year_label(row)} {_fmt_plain_pct(calc_dividend_yield_pct(price, row.dividend))}" for row in dividend_rows]
    market_per = _fmt_market_per((market_snapshot or {}).get("per"))
    if not per_lines and market_per is not None:
        per_lines = [f"市場PER {market_per}"]

    indicator_lines = build_indicator_lines(
        price=price,
        market_cap=market_cap,
        industry=industry_name,
        pbr=(market_snapshot or {}).get("pbr"),
        roe=(market_snapshot or {}).get("roe"),
    )
    valuation_lines = _build_valuation_lines(per_lines, dividend_lines)
    return "\n".join([f"【銘柄】{company_name} ({code4})", *indicator_lines, *valuation_lines, *build_analyst_estimates_lines(analyst_estimates, price=price)])
