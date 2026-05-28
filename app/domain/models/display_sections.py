from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class SummarySection:
    company_name: str
    code4: str
    price: float | None
    market_cap: float | None
    industry: str
    pbr: float | None
    roe: float | None


@dataclass
class ValuationTableSection:
    year_labels: List[str]
    per_values: List[str]
    dividend_values: List[str]


Section = SummarySection | ValuationTableSection


@dataclass
class DisplaySections:
    sections: List[Section]
