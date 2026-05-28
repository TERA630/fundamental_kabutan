"""Formatter: convert domain display DTOs into plain-text sections."""
from __future__ import annotations

from typing import List

from app.domain.models.display_sections import DisplaySections, SummarySection, ValuationTableSection


def format_summary(section: SummarySection) -> List[str]:
    lines: List[str] = []
    lines.append(f"【銘柄】{section.company_name} ({section.code4})")
    lines.append("■指標")
    price = "N/A" if section.price is None else f"{section.price:,.0f}"
    pbr = "N/A" if section.pbr is None else f"{section.pbr:.2f}"
    roe = "N/A" if section.roe is None else f"{section.roe:.2f}%"
    lines.append(f"株価：{price}円 / PBR {pbr} / ROE {roe}")
    cap_text = "N/A" if section.market_cap is None else f"{section.market_cap/100_000_000:,.1f}億円"
    lines.append(f"業種：{section.industry}　時価総額：{cap_text}")
    return lines


def format_valuation(section: ValuationTableSection) -> List[str]:
    header = "年度|" + "|".join(section.year_labels) if section.year_labels else "年度|N/A"
    per_line = f"PER|{'|'.join(section.per_values) if section.per_values else 'N/A'}"
    div_line = f"配当利回り|{'|'.join(section.dividend_values) if section.dividend_values else 'N/A'}"
    return ["", "■バリュエーション", header, per_line, div_line]


def format_sections(sections: DisplaySections) -> str:
    lines: List[str] = []
    for s in sections.sections:
        if isinstance(s, SummarySection):
            lines.extend(format_summary(s))
        elif isinstance(s, ValuationTableSection):
            lines.extend(format_valuation(s))
    return "\n".join(lines)
