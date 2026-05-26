"""Domain policy: rankCF scoring rules."""

from __future__ import annotations

from app.domain.models.cf_scoring_input import CfScoringInput
from app.domain.models.cf_scoring_result import CategoryScore, CfScoringResult, MetricScore, TotalScore

SCORING_VERSION = "rankcf-v1"


def _metric(metric_id: str, category: str, raw_value: float | None, rank: str, points: int, max_points: int, *notes: str) -> MetricScore:
    return MetricScore(
        metric_id=metric_id,
        category=category,  # type: ignore[arg-type]
        raw_value=raw_value,
        rank=rank,  # type: ignore[arg-type]
        points=points,
        max_points=max_points,
        rule_notes=tuple(note for note in notes if note),
    )


def score_roic(roic: float | None) -> MetricScore:
    if roic is None:
        return _metric("roic", "quality", None, "N/A", 0, 15)
    if roic >= 25:
        return _metric("roic", "quality", roic, "S", 15, 15)
    if roic >= 20:
        return _metric("roic", "quality", roic, "A", 12, 15)
    if roic >= 15:
        return _metric("roic", "quality", roic, "B", 9, 15)
    if roic >= 10:
        return _metric("roic", "quality", roic, "C", 6, 15)
    if roic >= 5:
        return _metric("roic", "quality", roic, "D", 3, 15)
    return _metric("roic", "quality", roic, "E", 0, 15)


def score_cash_conversion_np(ocf: float | None, net_income: float | None) -> MetricScore:
    if ocf is None or net_income in (None, 0):
        return _metric("cash_conversion_np", "quality", None, "N/A", 0, 15)
    if net_income <= 0:
        return _metric("cash_conversion_np", "quality", ocf / net_income, "E", 0, 15, "invalid_sign: net_income <= 0")
    if ocf <= 0:
        return _metric("cash_conversion_np", "quality", ocf / net_income, "E", 0, 15, "invalid_sign: ocf <= 0")
    ratio = ocf / net_income
    if ratio < 0.3:
        return _metric("cash_conversion_np", "quality", ratio, "E", 0, 15)
    if ratio < 0.5:
        return _metric("cash_conversion_np", "quality", ratio, "D", 2, 15)
    if ratio < 0.8:
        return _metric("cash_conversion_np", "quality", ratio, "C", 5, 15)
    if ratio < 1.0:
        return _metric("cash_conversion_np", "quality", ratio, "B", 9, 15)
    if ratio < 1.3:
        return _metric("cash_conversion_np", "quality", ratio, "A", 12, 15)
    return _metric("cash_conversion_np", "quality", ratio, "S", 15, 15)


def apply_quality_filter_ocf_op(metric: MetricScore, ocf: float | None, operating_income: float | None) -> MetricScore:
    if ocf is None or operating_income in (None, 0):
        return metric
    ocf_op = ocf / operating_income
    if ocf_op >= 0.7 or metric.points <= 5:
        return metric
    return MetricScore(
        metric_id=metric.metric_id,
        category=metric.category,
        raw_value=metric.raw_value,
        rank="C",
        points=5,
        max_points=metric.max_points,
        rule_notes=metric.rule_notes + ("quality_filter: ocf/op < 0.7 capped to C(5)",),
    )


def score_ocf_margin(ocf: float | None, revenue: float | None) -> MetricScore:
    if ocf is None or revenue in (None, 0):
        return _metric("ocf_margin", "quality", None, "N/A", 0, 10)
    margin = (ocf / revenue) * 100
    if margin >= 20:
        return _metric("ocf_margin", "quality", margin, "S", 10, 10)
    if margin >= 15:
        return _metric("ocf_margin", "quality", margin, "A", 8, 10)
    if margin >= 10:
        return _metric("ocf_margin", "quality", margin, "B", 6, 10)
    if margin >= 5:
        return _metric("ocf_margin", "quality", margin, "C", 3, 10)
    if margin >= 0:
        return _metric("ocf_margin", "quality", margin, "D", 1, 10)
    return _metric("ocf_margin", "quality", margin, "E", 0, 10)


def score_op_margin(operating_income: float | None, revenue: float | None) -> MetricScore:
    if operating_income is None or revenue in (None, 0):
        return _metric("op_margin", "quality", None, "N/A", 0, 10)
    margin = (operating_income / revenue) * 100
    if margin >= 25:
        return _metric("op_margin", "quality", margin, "S", 10, 10)
    if margin >= 15:
        return _metric("op_margin", "quality", margin, "A", 8, 10)
    if margin >= 10:
        return _metric("op_margin", "quality", margin, "B", 5, 10)
    if margin >= 5:
        return _metric("op_margin", "quality", margin, "C", 2, 10)
    return _metric("op_margin", "quality", margin, "D", 0, 10)


def score_fcf_ratio(fcf: float | None, ocf: float | None, sales_cagr_3y: float | None, roic: float | None) -> MetricScore:
    if fcf is None or ocf in (None, 0):
        return _metric("fcf_ratio", "quality", None, "N/A", 0, 10)
    if ocf <= 0:
        return _metric("fcf_ratio", "quality", (fcf / ocf) * 100, "C", 0, 10, "invalid_sign: ocf <= 0")
    if fcf < 0:
        return _metric("fcf_ratio", "quality", (fcf / ocf) * 100, "C", 0, 10, "invalid_sign: fcf < 0")
    ratio = (fcf / ocf) * 100
    if ratio >= 60:
        metric = _metric("fcf_ratio", "quality", ratio, "S", 10, 10)
    elif ratio >= 30:
        metric = _metric("fcf_ratio", "quality", ratio, "A", 7, 10)
    elif ratio >= 0:
        metric = _metric("fcf_ratio", "quality", ratio, "B", 4, 10)
    else:
        metric = _metric("fcf_ratio", "quality", ratio, "C", 0, 10)

    if ratio < 30 and sales_cagr_3y is not None and roic is not None and sales_cagr_3y > 15 and roic > 15:
        return MetricScore(
            metric_id=metric.metric_id,
            category=metric.category,
            raw_value=metric.raw_value,
            rank="A",
            points=7,
            max_points=metric.max_points,
            rule_notes=metric.rule_notes + ("growth_exemption: fcf_ratio promoted to A(7)",),
        )
    return metric


def score_eps_cagr_3y(eps_cagr_3y: float | None) -> MetricScore:
    if eps_cagr_3y is None:
        return _metric("eps_cagr_3y", "growth", None, "N/A", 0, 15)
    if eps_cagr_3y > 25:
        return _metric("eps_cagr_3y", "growth", eps_cagr_3y, "S", 15, 15)
    if eps_cagr_3y >= 15:
        return _metric("eps_cagr_3y", "growth", eps_cagr_3y, "A", 12, 15)
    if eps_cagr_3y >= 8:
        return _metric("eps_cagr_3y", "growth", eps_cagr_3y, "B", 8, 15)
    if eps_cagr_3y >= 0:
        return _metric("eps_cagr_3y", "growth", eps_cagr_3y, "C", 4, 15)
    return _metric("eps_cagr_3y", "growth", eps_cagr_3y, "D", 0, 15)


def score_sales_cagr_3y(sales_cagr_3y: float | None) -> MetricScore:
    if sales_cagr_3y is None:
        return _metric("sales_cagr_3y", "growth", None, "N/A", 0, 10)
    if sales_cagr_3y > 20:
        return _metric("sales_cagr_3y", "growth", sales_cagr_3y, "S", 10, 10)
    if sales_cagr_3y >= 12:
        return _metric("sales_cagr_3y", "growth", sales_cagr_3y, "A", 8, 10)
    if sales_cagr_3y >= 6:
        return _metric("sales_cagr_3y", "growth", sales_cagr_3y, "B", 5, 10)
    if sales_cagr_3y >= 0:
        return _metric("sales_cagr_3y", "growth", sales_cagr_3y, "C", 2, 10)
    return _metric("sales_cagr_3y", "growth", sales_cagr_3y, "D", 0, 10)


def score_fcf_yield(fcf_yield: float | None, sales_cagr_3y: float | None) -> MetricScore:
    if fcf_yield is None:
        return _metric("fcf_yield", "valuation", None, "N/A", 0, 10)
    if fcf_yield > 7:
        metric = _metric("fcf_yield", "valuation", fcf_yield, "S", 10, 10)
    elif fcf_yield >= 4:
        metric = _metric("fcf_yield", "valuation", fcf_yield, "A", 7, 10)
    elif fcf_yield >= 2:
        metric = _metric("fcf_yield", "valuation", fcf_yield, "B", 4, 10)
    elif fcf_yield >= 1:
        metric = _metric("fcf_yield", "valuation", fcf_yield, "C", 2, 10)
    else:
        metric = _metric("fcf_yield", "valuation", fcf_yield, "D", 0, 10)

    if fcf_yield < 1 and sales_cagr_3y is not None and sales_cagr_3y > 15:
        return MetricScore(
            metric_id=metric.metric_id,
            category=metric.category,
            raw_value=metric.raw_value,
            rank="C",
            points=2,
            max_points=metric.max_points,
            rule_notes=metric.rule_notes + ("growth_floor: fcf_yield raised to C(2)",),
        )
    return metric


def score_per(per: float | None, eps_cagr_3y: float | None) -> MetricScore:
    if per is None:
        return _metric("per", "valuation", None, "N/A", 0, 5)
    if per <= 0:
        return _metric("per", "valuation", per, "D", 0, 5, "invalid_per: per <= 0")
    high_growth = eps_cagr_3y is not None and eps_cagr_3y > 20
    if per < 15:
        return _metric("per", "valuation", per, "S", 5, 5)
    if per < 25:
        return _metric("per", "valuation", per, "A", 4, 5)
    if per < 35:
        return _metric("per", "valuation", per, "B", 3, 5)
    if per <= 50:
        if high_growth:
            return _metric("per", "valuation", per, "C", 2, 5, "high_growth_bonus: +1 point")
        return _metric("per", "valuation", per, "C", 1, 5)
    if high_growth:
        return _metric("per", "valuation", per, "D", 1, 5, "high_growth_bonus: +1 point")
    return _metric("per", "valuation", per, "D", 0, 5)


def build_total_judgement(total_points: int) -> str:
    if total_points >= 80:
        return "◎ 機関主導グロース候補"
    if total_points >= 60:
        return "○ 標準的な強銘柄"
    if total_points >= 40:
        return "△ バリュー・シクリカル"
    return "✕ 対象外"


def calculate_cf_score(input_data: CfScoringInput) -> CfScoringResult:
    cash_conv = score_cash_conversion_np(input_data.ocf, input_data.net_income)
    cash_conv = apply_quality_filter_ocf_op(cash_conv, input_data.ocf, input_data.operating_income)

    quality_metrics = (
        score_roic(input_data.roic),
        cash_conv,
        score_ocf_margin(input_data.ocf, input_data.revenue),
        score_op_margin(input_data.operating_income, input_data.revenue),
        score_fcf_ratio(input_data.fcf, input_data.ocf, input_data.sales_cagr_3y, input_data.roic),
    )
    growth_metrics = (
        score_eps_cagr_3y(input_data.eps_cagr_3y),
        score_sales_cagr_3y(input_data.sales_cagr_3y),
    )
    valuation_metrics = (
        score_fcf_yield(input_data.fcf_yield, input_data.sales_cagr_3y),
        score_per(input_data.per, input_data.eps_cagr_3y),
    )

    quality = CategoryScore("quality", sum(x.points for x in quality_metrics), 60, quality_metrics)
    growth = CategoryScore("growth", sum(x.points for x in growth_metrics), 25, growth_metrics)
    valuation = CategoryScore("valuation", sum(x.points for x in valuation_metrics), 15, valuation_metrics)
    total_points = quality.subtotal + growth.subtotal + valuation.subtotal
    total = TotalScore(total_points, 100, build_total_judgement(total_points), None)
    return CfScoringResult(SCORING_VERSION, input_data.as_of, quality, growth, valuation, total)


__all__ = [
    "SCORING_VERSION",
    "apply_quality_filter_ocf_op",
    "build_total_judgement",
    "calculate_cf_score",
    "score_cash_conversion_np",
    "score_eps_cagr_3y",
    "score_fcf_ratio",
    "score_fcf_yield",
    "score_ocf_margin",
    "score_op_margin",
    "score_per",
    "score_roic",
    "score_sales_cagr_3y",
]
