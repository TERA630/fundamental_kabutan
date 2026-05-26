"""Data layer repository for fetching and parsing Kabutan finance forecasts."""

from __future__ import annotations

import re
import warnings

from bs4 import BeautifulSoup
from pathlib import Path
from typing import TypedDict

from app.data.file_cache import FileCache
from app.domain.models.kabutan_balance_sheet import KabutanBalanceSheetRow
from app.domain.models.kabutan_cashflow import KabutanCashflowRow
from app.domain.models.kabutan_forecast import KabutanForecastPair, KabutanForecastRow
from app.domain.models.quarterly_financials import QuarterlyActual


KABUTAN_HEADER_ALIASES = {
    "revised_eps": ("1株益",),
    "dividend": ("配当", "1株配"),
}

KABUTAN_CASH_STOCK_BALANCE_TOKENS = (
    "現金等期末残高",
    "期末現金等残高",
    "現金等残高",
    "現金等期末",
)

KABUTAN_CASH_STOCK_EXCLUDE_TOKENS = (
    "増減",
    "前年差",
    "前期比",
)

KABUTAN_BALANCE_SHEET_HEADER_ALIASES = {
    "bps": ("1株純資産", "１株純資産"),
    "equity_ratio": ("自己資本比率",),
    "total_assets": ("総資産",),
    "equity": ("自己資本",),
    "retained_earnings": ("剰余金",),
    "interest_bearing_debt_multiple": ("有利子負債倍率",),
}

KABUTAN_QUARTERLY_HEADER_ALIASES = {
    "period": ("決算期",),
    "sales": ("売上高",),
    "operating_profit": ("営業益", "営業利益"),
    "ordinary_profit": ("経常益", "経常利益"),
    "final_profit": ("最終益", "最終利益"),
    "revised_eps": ("修正1株益",),
    "operating_margin": ("売上営業損益率",),
}


class KabutanCacheRow(TypedDict):
    fiscal_year: str
    forecast_type: str
    period_type: str
    sales: int | None
    op_income: int | None
    ordinary_income: int | None
    np: int | None
    eps: float | None
    div: float | None


def _to_int(text: str) -> int | None:
    normalized = text.replace(",", "").replace("－", "").strip()
    return int(normalized) if normalized else None


def _to_float(text: str) -> float | None:
    normalized = text.replace(",", "").replace("－", "").strip()
    return float(normalized) if normalized else None


def _parse_period(text: str) -> tuple[str, int, int] | None:
    match = re.search(r"(\d{4})\.(\d{2})", text)
    if not match:
        return None
    return match.group(0), int(match.group(1)), int(match.group(2))


def _clean_cell_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _normalize_quarterly_header(text: str) -> str:
    cleaned = _clean_cell_text(text)
    cleaned = cleaned.replace(" ", "").replace("\u3000", "")
    return cleaned


def _parse_quarter_period(text: str) -> tuple[int, int] | None:
    match = re.search(r"(\d{4})\.(\d{2})(?:-(\d{2}))?", text)
    if not match:
        return None
    year = int(match.group(1))
    start_month = int(match.group(2))
    end_month = int(match.group(3)) if match.group(3) else start_month
    return year, end_month


def _build_quarterly_header_indices(header_cells: list[str]) -> dict[str, int | None]:
    normalized = [_normalize_quarterly_header(x) for x in header_cells]

    def _find_idx(tokens: tuple[str, ...]) -> int | None:
        return next((idx for idx, col in enumerate(normalized) if any(token in col for token in tokens)), None)

    return {key: _find_idx(tokens) for key, tokens in KABUTAN_QUARTERLY_HEADER_ALIASES.items()}


def _is_valid_quarterly_header(indices: dict[str, int | None]) -> bool:
    # Proposal A: core columns are required; some columns are optional and can be N/A in display.
    required_core = ("period", "sales", "operating_profit", "ordinary_profit", "revised_eps")
    return all(indices.get(k) is not None for k in required_core)


def _build_quarterly_actual_from_cells(cells: list[str], indices: dict[str, int | None], *, ticker: str) -> QuarterlyActual | None:
    period_idx = indices.get("period")
    if period_idx is None or len(cells) <= period_idx:
        return None
    period_text = cells[period_idx]
    if "予" in period_text:
        return None
    parsed_period = _parse_quarter_period(period_text)
    if parsed_period is None:
        return None
    year, end_month = parsed_period

    def _int_val(key: str) -> int | None:
        idx = indices.get(key)
        if idx is None or len(cells) <= idx:
            return None
        return _to_int(cells[idx])

    def _float_val(key: str) -> float | None:
        idx = indices.get(key)
        if idx is None or len(cells) <= idx:
            return None
        text = cells[idx].replace("%", "")
        return _to_float(text)

    return QuarterlyActual(
        ticker=ticker,
        fiscal_year=year,
        quarter=None,
        quarter_end_month=end_month,
        sales=_int_val("sales"),
        ordinary_profit=_int_val("ordinary_profit"),
        operating_profit=_int_val("operating_profit"),
        final_profit=_int_val("final_profit"),
        revised_eps=_float_val("revised_eps"),
        operating_margin=_float_val("operating_margin"),
    )


def parse_kabutan_quarterly_actual_rows(html: str, *, ticker: str) -> list[QuarterlyActual]:
    soup = BeautifulSoup(html, "html.parser")
    blocks = soup.select("div.fin_quarter_result_d")
    if not blocks:
        warnings.warn(
            "四半期テーブル探索: div.fin_quarter_result_d が見つかりませんでした",
            RuntimeWarning,
            stacklevel=2,
        )
        return []

    for block in blocks:
        for table in block.find_all("table"):
            header_indices: dict[str, int | None] | None = None
            rows: list[QuarterlyActual] = []
            for tr in table.find_all("tr"):
                cells = tr.find_all(["th", "td"])
                if not cells:
                    continue
                cleaned = [_clean_cell_text(c.get_text(" ", strip=True)) for c in cells]
                if header_indices is None:
                    maybe = _build_quarterly_header_indices(cleaned)
                    if _is_valid_quarterly_header(maybe):
                        header_indices = maybe
                    continue

                row = _build_quarterly_actual_from_cells(cleaned, header_indices, ticker=ticker)
                if row is not None:
                    rows.append(row)
            if rows:
                return rows

    warnings.warn(
        "四半期テーブル探索: ブロックは見つかりましたが、有効な四半期実績行を抽出できませんでした",
        RuntimeWarning,
        stacklevel=2,
    )
    return []


def _find_kabutan_result_blocks(html: str) -> list[BeautifulSoup]:
    soup = BeautifulSoup(html, "html.parser")
    blocks = soup.select("div.fin_year_result_d")
    if not blocks:
        raise ValueError("通期・業績推移テーブルが見つかりません")
    return blocks


def _get_kabutan_header_index(header_cells: list[str], metric_key: str) -> int | None:
    aliases = KABUTAN_HEADER_ALIASES.get(metric_key, ())
    return next((idx for idx, col in enumerate(header_cells) if any(alias in col for alias in aliases)), None)


def fetch_kabutan_header_indices(header_cells: list[str]) -> dict[str, int | None]:
    return {
        "revised_eps": _get_kabutan_header_index(header_cells, "revised_eps"),
        "dividend": _get_kabutan_header_index(header_cells, "dividend"),
    }


def build_kabutan_forecast_row_from_cells(cleaned_cells: list[str], header_indices: dict[str, int | None]) -> KabutanForecastRow | None:
    parsed_period = _parse_period(cleaned_cells[0])
    if parsed_period is None:
        return None

    period_label, year, month = parsed_period
    heading = cleaned_cells[0]
    revised_eps_idx = header_indices.get("revised_eps")
    dividend_idx = header_indices.get("dividend")
    return KabutanForecastRow(
        period_label=period_label,
        year=year,
        month=month,
        section="予想" if "予" in heading else "実績",
        sales=_to_int(cleaned_cells[1]),
        operating_profit=_to_int(cleaned_cells[2]),
        ordinary_profit=_to_int(cleaned_cells[3]),
        final_profit=_to_int(cleaned_cells[4]),
        revised_eps=_to_float(cleaned_cells[revised_eps_idx]) if revised_eps_idx is not None and len(cleaned_cells) > revised_eps_idx else None,
        dividend=_to_float(cleaned_cells[dividend_idx]) if dividend_idx is not None and len(cleaned_cells) > dividend_idx else None,
    )


def build_kabutan_cache_row(row: KabutanForecastRow) -> KabutanCacheRow:
    return {
        "fiscal_year": f"{row.year}/{row.month:02d}",
        "forecast_type": row.section,
        "period_type": "通期",
        "sales": row.sales,
        "op_income": row.operating_profit,
        "ordinary_income": row.ordinary_profit,
        "np": row.final_profit,
        "eps": row.revised_eps,
        "div": row.dividend,
    }


def build_kabutan_forecast_row_from_cache(cache_row: KabutanCacheRow) -> KabutanForecastRow:
    fiscal_year = str(cache_row["fiscal_year"])
    year_text, month_text = fiscal_year.split("/")
    return KabutanForecastRow(
        period_label=fiscal_year.replace("/", "."),
        year=int(year_text),
        month=int(month_text),
        section=str(cache_row.get("forecast_type", "実績")),
        sales=cache_row.get("sales"),
        operating_profit=cache_row.get("op_income"),
        ordinary_profit=cache_row.get("ordinary_income"),
        final_profit=cache_row.get("np"),
        revised_eps=cache_row.get("eps"),
        dividend=cache_row.get("div"),
    )


def fetch_kabutan_forecast_rows_from_cache_payload(cached_payload: dict[str, object]) -> list[KabutanForecastRow]:
    rows = cached_payload.get("rows")
    if not isinstance(rows, list) or not rows:
        return []

    parsed_rows: list[KabutanForecastRow] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            parsed_rows.append(build_kabutan_forecast_row_from_cache(row))
        except (KeyError, ValueError, TypeError):
            continue
    return parsed_rows


def _parse_kabutan_forecast_rows(html: str) -> list[KabutanForecastRow]:
    rows: list[KabutanForecastRow] = []
    for block in _find_kabutan_result_blocks(html):
        header_cells: list[str] = []
        header_indices = {"revised_eps": None, "dividend": None}
        for table in block.find_all("table"):
            for row in table.find_all("tr"):
                cells = row.find_all(["th", "td"])
                if len(cells) < 5:
                    continue
                cleaned_cells = [_clean_cell_text(cell.get_text(" ", strip=True)) for cell in cells]
                if "売上高" in "".join(cleaned_cells):
                    header_cells = cleaned_cells
                    header_indices = fetch_kabutan_header_indices(header_cells)
                    continue
                parsed_row = build_kabutan_forecast_row_from_cells(cleaned_cells, header_indices)
                if parsed_row is not None:
                    rows.append(parsed_row)
    return rows


def _extract_kabutan_visible_body(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    block = soup.select_one("div.fin_year_result_d")
    if block is None:
        return html
    return str(block)


def _normalize_kabutan_cashflow_header(text: str) -> str:
    cleaned = _clean_cell_text(text)
    cleaned = cleaned.replace("(百万円)", "")
    cleaned = cleaned.replace("（百万円）", "")
    cleaned = cleaned.replace(" ", "").replace("\u3000", "")
    return cleaned


def _build_kabutan_cashflow_header_indices(header_cells: list[str]) -> dict[str, int | None]:
    normalized = [_normalize_kabutan_cashflow_header(x) for x in header_cells]

    def _find_idx(token: str) -> int | None:
        return next((idx for idx, col in enumerate(normalized) if token in col), None)

    def _find_first_idx(tokens: tuple[str, ...]) -> int | None:
        for token in tokens:
            idx = _find_idx(token)
            if idx is not None:
                return idx
        return None

    def _find_cash_stock_idx() -> int | None:
        by_balance_token = _find_first_idx(KABUTAN_CASH_STOCK_BALANCE_TOKENS)
        if by_balance_token is not None:
            return by_balance_token
        for idx, col in enumerate(normalized):
            if "現金等" not in col:
                continue
            if any(token in col for token in KABUTAN_CASH_STOCK_EXCLUDE_TOKENS):
                continue
            return idx
        return None

    return {
        "period": _find_idx("決算期"),
        "free_cf": _find_idx("フリーCF"),
        "operating_cf": _find_idx("営業CF"),
        "investing_cf": _find_idx("投資CF"),
        "financing_cf": _find_idx("財務CF"),
        "cash_stock": _find_cash_stock_idx(),
    }


def _is_kabutan_cashflow_header(indices: dict[str, int | None]) -> bool:
    required = ("period", "free_cf", "operating_cf", "investing_cf", "financing_cf")
    return all(indices.get(k) is not None for k in required)


def _build_kabutan_cashflow_row_from_cells(cells: list[str], indices: dict[str, int | None]) -> KabutanCashflowRow | None:
    period_idx = indices.get("period")
    if period_idx is None or len(cells) <= period_idx:
        return None
    parsed_period = _parse_period(cells[period_idx])
    if parsed_period is None:
        return None
    period_label, year, month = parsed_period

    def _val(key: str) -> int | None:
        idx = indices.get(key)
        if idx is None or len(cells) <= idx:
            return None
        return _to_int(cells[idx])

    return KabutanCashflowRow(
        period_label=period_label,
        year=year,
        month=month,
        free_cf=_val("free_cf"),
        operating_cf=_val("operating_cf"),
        investing_cf=_val("investing_cf"),
        financing_cf=_val("financing_cf"),
        cash_stock=_val("cash_stock"),
    )


def parse_kabutan_cashflow_rows(html: str) -> list[KabutanCashflowRow]:
    soup = BeautifulSoup(html, "html.parser")
    result: list[KabutanCashflowRow] = []
    found_header = False

    for table in soup.find_all("table"):
        header_indices: dict[str, int | None] | None = None
        for tr in table.find_all("tr"):
            cells = tr.find_all(["th", "td"])
            if not cells:
                continue
            cleaned = [_clean_cell_text(c.get_text(" ", strip=True)) for c in cells]
            if header_indices is None:
                maybe_indices = _build_kabutan_cashflow_header_indices(cleaned)
                if _is_kabutan_cashflow_header(maybe_indices):
                    header_indices = maybe_indices
                    found_header = True
                    if header_indices.get("cash_stock") is None:
                        warnings.warn("CFテーブルに現金等残高列が見つからないため cash_stock は None になります", RuntimeWarning, stacklevel=2)
                continue

            row = _build_kabutan_cashflow_row_from_cells(cleaned, header_indices)
            if row is not None:
                result.append(row)

        if result:
            return result

    if not found_header:
        raise ValueError("キャッシュフロー(CF)テーブルのヘッダが見つかりません")
    raise ValueError("キャッシュフロー(CF)テーブルに有効な決算期データがありません")


def _normalize_kabutan_balance_sheet_header(text: str) -> str:
    cleaned = _clean_cell_text(text)
    cleaned = cleaned.replace("(百万円)", "").replace("（百万円）", "")
    cleaned = cleaned.replace("（％）", "").replace("(%)", "")
    cleaned = cleaned.replace(" ", "").replace("\u3000", "")
    cleaned = cleaned.replace("１", "1")
    return cleaned


def _build_kabutan_balance_sheet_header_indices(header_cells: list[str]) -> dict[str, int | None]:
    normalized = [_normalize_kabutan_balance_sheet_header(x) for x in header_cells]

    def _find_idx_by_aliases(aliases: tuple[str, ...], *, exclude: tuple[str, ...] = ()) -> int | None:
        for idx, col in enumerate(normalized):
            if not any(alias in col for alias in aliases):
                continue
            if exclude and any(token in col for token in exclude):
                continue
            return idx
        return None

    equity_ratio_idx = _find_idx_by_aliases(KABUTAN_BALANCE_SHEET_HEADER_ALIASES["equity_ratio"])
    equity_idx = _find_idx_by_aliases(KABUTAN_BALANCE_SHEET_HEADER_ALIASES["equity"], exclude=("比率",))

    return {
        "period": next((idx for idx, col in enumerate(normalized) if "決算期" in col), None),
        "bps": _find_idx_by_aliases(KABUTAN_BALANCE_SHEET_HEADER_ALIASES["bps"]),
        "equity_ratio": equity_ratio_idx,
        "total_assets": _find_idx_by_aliases(KABUTAN_BALANCE_SHEET_HEADER_ALIASES["total_assets"]),
        "equity": equity_idx,
        "retained_earnings": _find_idx_by_aliases(KABUTAN_BALANCE_SHEET_HEADER_ALIASES["retained_earnings"]),
        "interest_bearing_debt_multiple": _find_idx_by_aliases(
            KABUTAN_BALANCE_SHEET_HEADER_ALIASES["interest_bearing_debt_multiple"]
        ),
    }


def _count_kabutan_balance_sheet_coverage(indices: dict[str, int | None]) -> int:
    metric_keys = (
        "bps",
        "equity_ratio",
        "total_assets",
        "equity",
        "retained_earnings",
        "interest_bearing_debt_multiple",
    )
    return sum(1 for key in metric_keys if indices.get(key) is not None)


def _is_kabutan_balance_sheet_header(indices: dict[str, int | None]) -> bool:
    if indices.get("period") is None:
        return False
    return _count_kabutan_balance_sheet_coverage(indices) >= 4


def _build_kabutan_balance_sheet_row_from_cells(cells: list[str], indices: dict[str, int | None]) -> KabutanBalanceSheetRow | None:
    period_idx = indices.get("period")
    if period_idx is None or len(cells) <= period_idx:
        return None
    parsed_period = _parse_period(cells[period_idx])
    if parsed_period is None:
        return None
    period_label, year, month = parsed_period

    def _int_val(key: str) -> int | None:
        idx = indices.get(key)
        if idx is None or len(cells) <= idx:
            return None
        return _to_int(cells[idx])

    def _float_val(key: str) -> float | None:
        idx = indices.get(key)
        if idx is None or len(cells) <= idx:
            return None
        return _to_float(cells[idx])

    return KabutanBalanceSheetRow(
        period_label=period_label,
        year=year,
        month=month,
        bps=_float_val("bps"),
        equity_ratio=_float_val("equity_ratio"),
        total_assets=_int_val("total_assets"),
        equity=_int_val("equity"),
        retained_earnings=_int_val("retained_earnings"),
        interest_bearing_debt_multiple=_float_val("interest_bearing_debt_multiple"),
    )


def _select_kabutan_balance_sheet_table(soup: BeautifulSoup) -> BeautifulSoup | None:
    selectors = ("#wrapper_main>#container>#main>#finance_box table", "#finance_box table")
    seen_ids: set[int] = set()
    tables: list[BeautifulSoup] = []
    for selector in selectors:
        for table in soup.select(selector):
            table_id = id(table)
            if table_id in seen_ids:
                continue
            seen_ids.add(table_id)
            tables.append(table)

    best: tuple[int, int, int, BeautifulSoup] | None = None
    for order, table in enumerate(tables):
        header_indices: dict[str, int | None] | None = None
        row_count = 0
        for tr in table.find_all("tr"):
            cells = tr.find_all(["th", "td"])
            if not cells:
                continue
            cleaned = [_clean_cell_text(c.get_text(" ", strip=True)) for c in cells]
            if header_indices is None:
                maybe_indices = _build_kabutan_balance_sheet_header_indices(cleaned)
                if _is_kabutan_balance_sheet_header(maybe_indices):
                    header_indices = maybe_indices
                continue
            if _build_kabutan_balance_sheet_row_from_cells(cleaned, header_indices) is not None:
                row_count += 1

        if header_indices is None:
            continue
        score = (_count_kabutan_balance_sheet_coverage(header_indices), row_count, -order)
        if best is None or score > (best[0], best[1], best[2]):
            best = (score[0], score[1], score[2], table)

    return None if best is None else best[3]


def parse_kabutan_balance_sheet_rows(html: str) -> list[KabutanBalanceSheetRow]:
    soup = BeautifulSoup(html, "html.parser")
    table = _select_kabutan_balance_sheet_table(soup)
    if table is None:
        raise ValueError("バランスシート(BS)テーブルのヘッダが見つかりません")

    header_indices: dict[str, int | None] | None = None
    result: list[KabutanBalanceSheetRow] = []
    for tr in table.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        if not cells:
            continue
        cleaned = [_clean_cell_text(c.get_text(" ", strip=True)) for c in cells]
        if header_indices is None:
            maybe_indices = _build_kabutan_balance_sheet_header_indices(cleaned)
            if _is_kabutan_balance_sheet_header(maybe_indices):
                header_indices = maybe_indices
            continue

        row = _build_kabutan_balance_sheet_row_from_cells(cleaned, header_indices)
        if row is not None:
            result.append(row)

    if not result:
        raise ValueError("バランスシート(BS)テーブルに有効な決算期データがありません")
    return result


def _build_forecast_pair_from_rows(rows: list[KabutanForecastRow], target_years: tuple[int, int] | None = None) -> KabutanForecastPair:
    forecast_idx = next((idx for idx, row in enumerate(rows) if row.section == "予想"), None)
    if forecast_idx is None:
        raise ValueError("予想行が見つかりません")

    current_forecast = rows[forecast_idx]
    next_forecast = rows[forecast_idx + 1] if len(rows) > forecast_idx + 1 and rows[forecast_idx + 1].section == "予想" else None
    current_actual = next((row for row in rows if row.section == "実績" and row.year == current_forecast.year), None)
    anchor_year = current_actual.year if current_actual is not None else current_forecast.year
    prior_actuals = sorted([row for row in rows if row.section == "実績" and row.year < anchor_year], key=lambda x: x.year)
    previous_actual = prior_actuals[-1] if prior_actuals else None
    previous2_actual = prior_actuals[-2] if len(prior_actuals) >= 2 else None

    if target_years is not None:
        year_set = set(target_years)
        if current_forecast.year not in year_set:
            raise ValueError(f"今期予想の年度 {current_forecast.year} が対象年度 {sorted(year_set)} に含まれません")
        if next_forecast is not None and next_forecast.year not in year_set:
            next_forecast = None

    return KabutanForecastPair(
        previous2_actual=previous2_actual,
        previous_actual=previous_actual,
        current_actual=current_actual,
        current_forecast=current_forecast,
        next_forecast=next_forecast,
        all_rows=tuple(rows),
    )


def infer_fiscal_year_end_month_from_forecast_rows(rows: list[KabutanForecastRow]) -> int | None:
    if not rows:
        return None
    prioritized = [row.month for row in rows if row.section == "実績"]
    months = prioritized or [row.month for row in rows]
    if not months:
        return None
    counts: dict[int, int] = {}
    for month in months:
        counts[month] = counts.get(month, 0) + 1
    return max(sorted(counts.keys()), key=lambda m: counts[m])


class KabutanForecastRepository:
    def __init__(self, timeout_sec: int = 10, file_cache: FileCache | None = None):
        self.timeout_sec = timeout_sec
        self.file_cache = file_cache or FileCache()

    @staticmethod
    def build_cache_key_kabutan_forecast(code: str) -> str:
        return f"kabutan_forecast_{code}"

    @staticmethod
    def build_cache_key_kabutan_html(path: Path) -> str:
        return f"kabutan_html_{path.resolve()}"

    def fetch_kabutan_html_from_file(self, html_path: str | Path) -> str:
        path = Path(html_path)
        cache_key = self.build_cache_key_kabutan_html(path)
        cached_html = self.file_cache.get(cache_key, ttl_sec=365 * 24 * 60 * 60)
        if isinstance(cached_html, str) and cached_html:
            return cached_html
        html = path.read_text(encoding="utf-8")
        visible_html = _extract_kabutan_visible_body(html)
        self.file_cache.set(cache_key, visible_html)
        return visible_html

    def fetch_kabutan_forecast_pair_from_file(self, html_path: str | Path, target_years: tuple[int, int] | None = None) -> KabutanForecastPair:
        html = self.fetch_kabutan_html_from_file(html_path)
        return self._fetch_forecast_pair_from_html(html, target_years=target_years)

    def fetch_kabutan_cashflow_rows_from_file(self, html_path: str | Path) -> tuple[KabutanCashflowRow, ...]:
        html = Path(html_path).read_text(encoding="utf-8")
        return tuple(parse_kabutan_cashflow_rows(html))

    def fetch_kabutan_balance_sheet_rows_from_file(self, html_path: str | Path) -> tuple[KabutanBalanceSheetRow, ...]:
        html = Path(html_path).read_text(encoding="utf-8")
        return tuple(parse_kabutan_balance_sheet_rows(html))

    def fetch_kabutan_quarterly_actual_rows_from_file(self, html_path: str | Path, *, ticker: str) -> tuple[QuarterlyActual, ...]:
        html = Path(html_path).read_text(encoding="utf-8")
        return tuple(parse_kabutan_quarterly_actual_rows(html, ticker=ticker))

    @staticmethod
    def get_kabutan_cache_payload(pair: KabutanForecastPair) -> dict[str, object]:
        rows = []
        source_rows = pair.all_rows if pair.all_rows else (
            pair.previous2_actual,
            pair.previous_actual,
            pair.current_actual,
            pair.current_forecast,
            pair.next_forecast,
        )
        for row in source_rows:
            if row is None:
                continue
            rows.append(build_kabutan_cache_row(row))
        return {"rows": rows}

    def _fetch_forecast_pair_from_html(self, html: str, target_years: tuple[int, int] | None = None) -> KabutanForecastPair:
        rows = _parse_kabutan_forecast_rows(html)
        return _build_forecast_pair_from_rows(rows, target_years=target_years)

    def fetch_kabutan_forecast_pair(self, code: str, target_years: tuple[int, int] | None = None) -> KabutanForecastPair:
        cache_key = self.build_cache_key_kabutan_forecast(code)
        cached_payload = self.file_cache.get(cache_key, ttl_sec=12 * 60 * 60)
        if isinstance(cached_payload, dict):
            parsed_rows = fetch_kabutan_forecast_rows_from_cache_payload(cached_payload)
            if parsed_rows:
                return _build_forecast_pair_from_rows(parsed_rows, target_years=target_years)
        raise RuntimeError("Web取得は無効です。HTMLファイル入力を使用してください。")


__all__ = [
    "KabutanForecastRepository",
    "_parse_kabutan_forecast_rows",
    "_extract_kabutan_visible_body",
    "parse_kabutan_quarterly_actual_rows",
]
