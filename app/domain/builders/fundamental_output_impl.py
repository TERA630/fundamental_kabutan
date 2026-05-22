"""Domain output implementation without legacy module dependency."""

from __future__ import annotations

from datetime import date
from typing import Any



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




def build_indicator_lines(
    *,
    price: float | None,
    market_cap: float | None,
    industry: str,
    pbr: float | None,
    roe: float | None,
    per_actual: float | None,
    per_current_forecast: float | None,
    per_next_forecast: float | None,
    div_actual: float | None,
    div_current_forecast: float | None,
    div_next_forecast: float | None,
    base_year: int,
) -> list[str]:
    return [
        "■指標",
        f"株価：{_fmt_num(price,0)}円 / PBR {_fmt_num(pbr)} / ROE {_fmt_plain_pct(roe)}",
        f"業種：{industry}　時価総額：{_fmt_money(market_cap)}({_build_market_cap_rank(market_cap)})",
        f"PER：{base_year}年実績 {_fmt_num(per_actual,1)}倍／{base_year + 1}年末予想 {_fmt_num(per_current_forecast,1)}倍／{base_year + 2}年来期予想 {_fmt_num(per_next_forecast,1)}倍",
        f"配当利回り：{base_year}年実績 {_fmt_plain_pct(div_actual)}／{base_year + 1}年末予想 {_fmt_plain_pct(div_current_forecast)}／{base_year + 2}年来季予想 {_fmt_plain_pct(div_next_forecast)}",
    ]


def build_fundamental_output_text_impl(*, name: str, code4: str, master: dict[str, Any] | None, price: float | None, market_cap: float | None, market_snapshot: dict[str, Any] | None = None) -> str:
    company_name = str(_first_present(master, ["CompanyName", "Name", "LocalCodeName"]) or name)
    industry_name = str((market_snapshot or {}).get("industry") or _first_present(master, ["S33Nm", "Sector33CodeName", "Sector33Name"]) or "N/A")

    base_year = int((market_snapshot or {}).get("base_year") or date.today().year)

    indicator_lines = build_indicator_lines(
        price=price,
        market_cap=market_cap,
        industry=industry_name,
        pbr=(market_snapshot or {}).get("pbr"),
        roe=(market_snapshot or {}).get("roe"),
        per_actual=(market_snapshot or {}).get("per"),
        per_current_forecast=(market_snapshot or {}).get("per_current_forecast"),
        per_next_forecast=(market_snapshot or {}).get("per_next_forecast"),
        div_actual=(market_snapshot or {}).get("div_yield"),
        div_current_forecast=(market_snapshot or {}).get("div_yield_current_forecast"),
        div_next_forecast=(market_snapshot or {}).get("div_yield_next_forecast"),
        base_year=base_year,
    )
    return "\n".join([f"【銘柄】{company_name} ({code4})", *indicator_lines])
