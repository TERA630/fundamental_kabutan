from __future__ import annotations

from dataclasses import dataclass
from typing import List

from app.domain.models.cf_scoring_result import MetricScore
from app.domain.models.kabutan_cashflow import KabutanCashflowRow
from app.domain.models.kabutan_forecast import KabutanForecastRow
from app.domain.models.quarterly_financials import QuarterlyMetricRow


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
class OpeningSummarySection:
    company_name: str
    code4: str
    price: float | None
    market_cap: float | None
    market_cap_class: str | None
    judgement: str | None
    total_points: int | None
    max_points: int | None
    growth_phase: str | None
    per_level: str | None
    roic_level: str | None
    investment_strategy: str | None


@dataclass
class ValuationTableSection:
    year_labels: List[str]
    per_values: List[str]
    dividend_values: List[str]
    pbr_values: List[str] | None = None
    roe_values: List[str] | None = None
    roic_values: List[str] | None = None
    fcf_yield_values: List[str] | None = None


@dataclass
class ScoreSummarySection:
    judgement: str
    total_points: int
    max_points: int
    version: str
    investment_category: str
    investment_strategy: str
    as_of: str | None


@dataclass
class ScoreCategorySection:
    title: str
    subtotal: int
    max_points: int
    metrics: List[MetricScore]


@dataclass
class RuleNotesSection:
    notes: List[str]


@dataclass
class ForecastTableSection:
    source: str
    source_message: str | None
    rows: List[KabutanForecastRow]


@dataclass
class GrowthTimelineSection:
    rows: List[KabutanForecastRow]
    eps_growth_rates: List[float | None]
    operating_growth_rates: List[float | None]
    operating_cagr: float | None
    eps_cagr: float | None
    cagr_start_year: int | None
    cagr_end_year: int | None


@dataclass
class CashflowMetricDisplayRow:
    year: int
    cash_conversion_pct: float | None
    fcf_yield_pct: float | None
    fcf_margin_pct: float | None
    operating_cf_margin_pct: float | None
    investment_aggressiveness_pct: float | None


@dataclass
class CashflowTimelineSection:
    actual_rows: List[KabutanCashflowRow]
    metric_rows: List[CashflowMetricDisplayRow]


@dataclass
class FinancialMetricDisplayRow:
    year: int
    roe_pct: float | None
    roic_pct: float | None
    pbr: float | None


@dataclass
class FinancialMetricsSection:
    rows: List[FinancialMetricDisplayRow]


@dataclass
class QuarterlyMetricsSection:
    rows: List[QuarterlyMetricRow]
    message: str | None = None


Section = (
    SummarySection
    | OpeningSummarySection
    | ScoreSummarySection
    | ValuationTableSection
    | ScoreCategorySection
    | RuleNotesSection
    | ForecastTableSection
    | GrowthTimelineSection
    | CashflowTimelineSection
    | FinancialMetricsSection
    | QuarterlyMetricsSection
)


@dataclass
class DisplaySections:
    sections: List[Section]
