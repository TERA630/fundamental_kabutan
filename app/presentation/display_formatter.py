"""Formatter: convert domain display DTOs into plain-text sections."""
from __future__ import annotations

import logging
from typing import List

from app.domain.models.cf_scoring_result import MetricScore
from app.domain.models.display_sections import (
    CashflowTimelineSection,
    DisplaySections,
    FinancialMetricsSection,
    ForecastTableSection,
    GrowthTimelineSection,
    QuarterlyMetricsSection,
    RuleNotesSection,
    ScoreCategorySection,
    ScoreSummarySection,
    SummarySection,
    ValuationTableSection,
)
from app.domain.models.kabutan_forecast import KabutanForecastRow


logger = logging.getLogger(__name__)

METRIC_LABELS = {
    "roic": "ROIC",
    "cash_conversion_np": "Cash Conversion(OCF/純利益)",
    "ocf_margin": "営業CFマージン",
    "op_margin": "営業利益率",
    "fcf_ratio": "FCF Ratio(FCF/OCF)",
    "eps_cagr_3y": "EPS CAGR(3y)",
    "sales_cagr_3y": "売上CAGR(3y)",
    "fcf_yield": "FCF Yield",
    "per": "PER",
}

RULE_NOTE_JA_MAP = {
    "high_growth_bonus": "高グロース株加点",
    "growth_floor": "高成長考慮による下限補正",
    "growth_exemption": "成長投資免責によるランク引き上げ",
    "quality_filter": "品質フィルター適用（OCF/営業利益）",
    "invalid_per": "PER算出値不正",
}

RULE_NOTE_EXACT_MAP = {
    "invalid_sign: net_income <= 0": "純利益符号不正",
    "invalid_sign: ocf <= 0": "営業CF符号不正",
    "invalid_sign: ocf == 0": "営業CFゼロ",
    "invalid_sign: ocf < 0": "営業CFマイナス",
}


def _fmt_oku(value: int | None) -> str:
    if value is None:
        return "N/A"
    return f"{value / 100:,.1f}億"


def _fmt_million_yen(value: int | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:,}"


def _fmt_yen(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:,.1f}円"


def _fmt_percent(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.1f}%"


def _fmt_multiplier(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.2f}倍"


def _fmt_ratio_or_blank(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:+.1f}%"


def _format_market_cap_rank(value: float | None) -> str:
    if value is None:
        return "N/A"
    oku = value / 100_000_000
    if oku >= 100_000:
        return "超大型"
    if oku >= 10_000:
        return "大型主役"
    if oku >= 3_000:
        return "中型主役"
    if oku >= 1_000:
        return "小〜中型"
    return "小型"


def format_summary(section: SummarySection) -> List[str]:
    lines: List[str] = []
    lines.append(f"【銘柄】{section.company_name} ({section.code4})")
    price = "N/A" if section.price is None else f"{section.price:,.0f}"
    lines.append(f"株価：{price}円")
    cap_text = "N/A" if section.market_cap is None else f"{section.market_cap/100_000_000:,.1f}億円"
    lines.append(f"時価総額：{cap_text}({_format_market_cap_rank(section.market_cap)})")
    return lines


def format_valuation(section: ValuationTableSection) -> List[str]:
    header = "年度|" + "|".join(section.year_labels) if section.year_labels else "年度|N/A"
    per_line = f"PER|{'|'.join(section.per_values) if section.per_values else 'N/A'}"
    div_line = f"配当利回り|{'|'.join(section.dividend_values) if section.dividend_values else 'N/A'}"
    return ["", "■バリュエーション", header, per_line, div_line]


def format_score_summary(section: ScoreSummarySection) -> List[str]:
    as_of = section.as_of[:7] if section.as_of and len(section.as_of) >= 7 else section.as_of
    return [
        f"総合評価：　{section.judgement} ({section.total_points}/{section.max_points}点) バージョン: {section.version}",
        f"投資分類： {section.investment_category}",
        f"投資戦略：　{section.investment_strategy}",
        f"算出基準： {as_of or 'N/A'}",
    ]


def _format_rule_note(note: str) -> str:
    if note in RULE_NOTE_EXACT_MAP:
        return RULE_NOTE_EXACT_MAP[note]
    key = note.split(":", 1)[0].strip()
    if key in RULE_NOTE_JA_MAP:
        return RULE_NOTE_JA_MAP[key]
    return f"未定義ルール: {note}"


def _format_metric_score(metric: MetricScore) -> str | None:
    label = METRIC_LABELS.get(metric.metric_id, metric.metric_id)
    if metric.raw_value is None:
        reason = "値欠損"
        logger.info("取得不可: %s (%s)", label, reason)
        logger.debug(
            "N/A項目を表示省略: metric_id=%s rank=%s points=%s/%s rule_notes=%s reason=%s",
            metric.metric_id,
            metric.rank,
            metric.points,
            metric.max_points,
            metric.rule_notes,
            reason,
        )
        return None

    raw = f"{metric.raw_value:.2f}"
    if metric.metric_id == "fcf_yield":
        raw = f"{metric.raw_value:.2f}%"
    return f"- {label}: {raw} -> {metric.rank}({metric.points}/{metric.max_points})"


def format_score_category(section: ScoreCategorySection) -> List[str]:
    lines = [f"{section.title}: {section.subtotal}/{section.max_points}"]
    for metric in section.metrics:
        formatted = _format_metric_score(metric)
        if formatted is not None:
            lines.append(formatted)
    return lines


def format_rule_notes(section: RuleNotesSection) -> List[str]:
    lines = ["ルール注記:"]
    if section.notes:
        lines.extend(f"- {_format_rule_note(note)}" for note in section.notes)
    else:
        lines.append("- なし")
    return lines


def _build_kabutan_source_label(source: str, message: str | None) -> str:
    source_label = {"html": "HTML", "none": "取得不可"}.get(source, "取得不可")
    return f"株探ソース: {source_label}" if not message else f"株探ソース: {source_label} ({message})"


def _build_profit_with_margin_text(profit: int | None, margin: float | None) -> str:
    return f"{_fmt_oku(profit)}({_fmt_percent(margin)})"


def _calc_operating_margin(sales: int | None, operating_profit: int | None) -> float | None:
    if sales is None or operating_profit is None or sales == 0:
        return None
    return (operating_profit / sales) * 100


def _calc_ordinary_margin(sales: int | None, ordinary_profit: int | None) -> float | None:
    if sales is None or ordinary_profit is None or sales == 0:
        return None
    return (ordinary_profit / sales) * 100


def _build_kabutan_row_line(row: KabutanForecastRow) -> str:
    year_label = f"{row.year}/{row.month:02d}(予)" if row.section == "予想" else f"{row.year}/{row.month:02d}"
    operating_margin = _calc_operating_margin(row.sales, row.operating_profit)
    ordinary_margin = _calc_ordinary_margin(row.sales, row.ordinary_profit)
    return (
        f"{year_label:<10}"
        f"{_fmt_oku(row.sales):>10}"
        f"{_build_profit_with_margin_text(row.operating_profit, operating_margin):>20}"
        f"{_build_profit_with_margin_text(row.ordinary_profit, ordinary_margin):>20}"
        f"{_fmt_oku(row.final_profit):>10}"
        f"{_fmt_yen(row.revised_eps):>10}"
        f"{_fmt_yen(row.dividend):>10}"
    )


def format_forecast_table(section: ForecastTableSection) -> List[str]:
    header = "　　　　　　売上　営業益(営業利益率)　経常益(経常利益率)　最終益　1株益　1株配当"
    row_lines = [_build_kabutan_row_line(row) for row in section.rows] if section.rows else ["データーが取得できません"]
    return [
        "",
        "■株探 通期業績推移",
        _build_kabutan_source_label(section.source, section.source_message),
        header,
        *row_lines,
    ]


def _build_growth_metric_line(title: str, rows: list[KabutanForecastRow], values: list[float | None]) -> str:
    parts = [title]
    for row, value in zip(rows, values):
        year_label = f"{row.year}/{row.month:02d}(予)" if row.section == "予想" else f"{row.year}/{row.month:02d}"
        parts.append(f"{year_label} {_fmt_percent(value)}")
    return "　".join(parts)


def _build_cagr_line(title: str, start_year: int | None, end_year: int | None, value: float | None) -> str:
    if start_year is None or end_year is None:
        return f"{title} N/A"
    return f"{title} {start_year}→{end_year} {_fmt_percent(value)}"


def format_growth_timeline(section: GrowthTimelineSection) -> List[str]:
    return [
        "■成長性",
        _build_growth_metric_line("EPS成長率", section.rows, section.eps_growth_rates),
        _build_growth_metric_line("営業利益成長率", section.rows, section.operating_growth_rates),
        _build_cagr_line("3年営業利益CAGR", section.cagr_start_year, section.cagr_end_year, section.operating_cagr),
        _build_cagr_line("3年EPS CAGR", section.cagr_start_year, section.cagr_end_year, section.eps_cagr),
    ]


def format_cashflow_timeline(section: CashflowTimelineSection) -> List[str]:
    if not section.actual_rows:
        return ["■キャッシュフロー", "N/A"]

    lines = [
        "■キャッシュフロー",
        "[A] CF実績（百万円）",
        "年度 | フリーCF | 営業CF | 投資CF | 財務CF | 現金等残高",
    ]
    for row in section.actual_rows:
        lines.append(
            f"{row.year} | {_fmt_million_yen(row.free_cf)} | {_fmt_million_yen(row.operating_cf)} | {_fmt_million_yen(row.investing_cf)} | {_fmt_million_yen(row.financing_cf)} | {_fmt_million_yen(row.cash_stock)}"
        )

    lines.extend(
        [
            "",
            "[B] 指標（%）",
            "年度 | Cash conversion | FCF Yield | FCFマージン | 営業CFマージン | 投資積極性",
        ]
    )
    for row in section.metric_rows:
        lines.append(
            f"{row.year} | {_fmt_percent(row.cash_conversion_pct)} | {_fmt_percent(row.fcf_yield_pct)} | {_fmt_percent(row.fcf_margin_pct)} | {_fmt_percent(row.operating_cf_margin_pct)} | {_fmt_percent(row.investment_aggressiveness_pct)}"
        )
    return lines


def format_financial_metrics(section: FinancialMetricsSection) -> List[str]:
    lines = ["■財務ブロック", "　　　ROE(%)|ROIC(%)|PBR|"]
    if not section.rows:
        lines.append("N/A")
        return lines
    for row in section.rows:
        lines.append(f"{row.year}年　{_fmt_percent(row.roe_pct)}|{_fmt_percent(row.roic_pct)}|{_fmt_multiplier(row.pbr)}")
    return lines


def format_quarterly_metrics(section: QuarterlyMetricsSection) -> List[str]:
    header = "　　　売上高|営業益(前年同期比%)|経常益|最終益|修正1株益(前年同期比%)|売上損益率|"
    if not section.rows:
        detail = f"N/A ({section.message})" if section.message else "N/A"
        return ["■四半期業績推移", header, detail]

    lines = ["■四半期業績推移", header]
    for row in section.rows:
        label = f"{row.fiscal_year}.{row.quarter_end_month}" if row.quarter_end_month is not None else str(row.fiscal_year)
        op = _fmt_oku(row.operating_profit)
        op_yoy = _fmt_ratio_or_blank(row.operating_profit_yoy_pct)
        eps = _fmt_yen(row.revised_eps)
        eps_yoy = _fmt_ratio_or_blank(row.revised_eps_yoy_pct)
        margin = _fmt_percent(row.operating_margin_pct) if row.operating_margin_pct is not None else "N/A"
        lines.append(f"{label}　{_fmt_oku(row.sales)}|{op}({op_yoy})|{_fmt_oku(row.ordinary_profit)}|{_fmt_oku(row.final_profit)}|{eps}({eps_yoy})|{margin}|")
    return lines


def format_sections(sections: DisplaySections) -> str:
    lines: List[str] = []
    for s in sections.sections:
        if isinstance(s, SummarySection):
            lines.extend(format_summary(s))
        elif isinstance(s, ScoreSummarySection):
            lines.extend(format_score_summary(s))
        elif isinstance(s, ValuationTableSection):
            lines.extend(format_valuation(s))
        elif isinstance(s, ScoreCategorySection):
            lines.extend(format_score_category(s))
        elif isinstance(s, RuleNotesSection):
            lines.extend(format_rule_notes(s))
        elif isinstance(s, ForecastTableSection):
            lines.extend(format_forecast_table(s))
        elif isinstance(s, GrowthTimelineSection):
            lines.extend(format_growth_timeline(s))
        elif isinstance(s, CashflowTimelineSection):
            lines.extend(format_cashflow_timeline(s))
        elif isinstance(s, FinancialMetricsSection):
            lines.extend(format_financial_metrics(s))
        elif isinstance(s, QuarterlyMetricsSection):
            lines.extend(format_quarterly_metrics(s))
    return "\n".join(lines)
