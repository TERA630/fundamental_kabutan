"""Domain output implementation without legacy module dependency."""

from __future__ import annotations

from typing import Any
from app.domain.models.kabutan_forecast import KabutanForecastPair, KabutanForecastRow



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




def build_indicator_lines(
    *,
    price: float | None,
    market_cap: float | None,
    industry: str,
    pbr: float | None,
    roe: float | None,
    per_lines: list[str],
    dividend_lines: list[str],
) -> list[str]:
    return [
        "■指標",
        f"株価：{_fmt_num(price,0)}円 / PBR {_fmt_num(pbr)} / ROE {_fmt_plain_pct(roe)}",
        f"業種：{industry}　時価総額：{_fmt_money(market_cap)}({_build_market_cap_rank(market_cap)})",
        "",
        f"PER：{'／'.join(per_lines) if per_lines else 'N/A'}",
        f"配当利回り：{'／'.join(dividend_lines) if dividend_lines else 'N/A'}",
    ]


def build_fundamental_output_text_impl(*, name: str, code4: str, master: dict[str, Any] | None, price: float | None, market_cap: float | None, market_snapshot: dict[str, Any] | None = None, kabutan_forecast_pair: KabutanForecastPair | None = None) -> str:
    company_name = str(_first_present(master, ["CompanyName", "Name", "LocalCodeName"]) or name)
    industry_name = str((market_snapshot or {}).get("industry") or _first_present(master, ["S33Nm", "Sector33CodeName", "Sector33Name"]) or "N/A")

    all_rows = fetch_kabutan_rows(kabutan_forecast_pair)
    per_rows = fetch_display_rows_for_indicator(all_rows, metric="per")
    dividend_rows = fetch_display_rows_for_indicator(all_rows, metric="dividend")
    per_lines = [f"{build_year_label(row)} {_fmt_num(calc_per_times(price, row.revised_eps),1)}倍" for row in per_rows]
    dividend_lines = [f"{build_year_label(row)} {_fmt_plain_pct(calc_dividend_yield_pct(price, row.dividend))}" for row in dividend_rows]

    indicator_lines = build_indicator_lines(
        price=price,
        market_cap=market_cap,
        industry=industry_name,
        pbr=(market_snapshot or {}).get("pbr"),
        roe=(market_snapshot or {}).get("roe"),
        per_lines=per_lines,
        dividend_lines=dividend_lines,
    )
    return "\n".join([f"【銘柄】{company_name} ({code4})", *indicator_lines])
