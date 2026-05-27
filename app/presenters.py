"""Presentation helpers: bridge GUI use-cases and domain/output builders."""

from __future__ import annotations
import logging
from typing import Any

from app.domain.builders.fundamental_output import build_fundamental_output_text
from app.domain.builders.kabutan_output import build_kabutan_forecast_output
from app.domain.models.cf_scoring_result import CfScoringResult, MetricScore
from app.domain.models.kabutan_cashflow import KabutanCashflowRow
from app.domain.models.kabutan_forecast import KabutanForecastPair
from app.domain.models.financial_snapshot import FinancialMetricInputRow
from app.domain.models.quarterly_financials import QuarterlyMetricRow


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

logger = logging.getLogger(__name__)

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

    raw = "N/A" if metric.raw_value is None else f"{metric.raw_value:.2f}"
    if metric.metric_id == "fcf_yield" and metric.raw_value is not None:
        raw = f"{metric.raw_value:.2f}%"
    return f"- {label}: {raw} -> {metric.rank}({metric.points}/{metric.max_points})"


def build_cf_scoring_summary_text(scoring: CfScoringResult) -> str:
    lines: list[str] = [
        "",
        "■rankCF スコア",
        f"バージョン: {scoring.version}",
        f"算出日: {scoring.as_of or 'N/A'}",
        f"合計: {scoring.total.total_points}/{scoring.total.max_points}",
        f"判定: {scoring.total.judgement}",
        f"Quality: {scoring.quality.subtotal}/{scoring.quality.max_points}",
    ]
    for metric in scoring.quality.metrics:
        formatted = _format_metric_score(metric)
        if formatted is not None:
            lines.append(formatted)
    lines.append(f"Growth: {scoring.growth.subtotal}/{scoring.growth.max_points}")
    for metric in scoring.growth.metrics:
        formatted = _format_metric_score(metric)
        if formatted is not None:
            lines.append(formatted)
    lines.append(f"Valuation: {scoring.valuation.subtotal}/{scoring.valuation.max_points}")
    for metric in scoring.valuation.metrics:
        formatted = _format_metric_score(metric)
        if formatted is not None:
            lines.append(formatted)

    notes = [note for category in (scoring.quality, scoring.growth, scoring.valuation) for metric in category.metrics for note in metric.rule_notes]
    lines.append("ルール注記:")
    if notes:
        lines.extend(f"- {_format_rule_note(note)}" for note in notes)
    else:
        lines.append("- なし")
    return "\n".join(lines)


def build_fundamental_output(
    *,
    name: str,
    code4: str,
    master: dict[str, Any] | None,
    price: float | None,
    market_cap: float | None,
    market_snapshot: dict[str, Any] | None = None,
    kabutan_forecast_pair: KabutanForecastPair | None = None,
    kabutan_source: str = "none",
    kabutan_source_message: str | None = None,
    kabutan_cashflow_rows: tuple[KabutanCashflowRow, ...] = (),
    financial_metric_rows: tuple[FinancialMetricInputRow, ...] = (),
    quarterly_metric_rows: tuple[QuarterlyMetricRow, ...] = (),
    quarterly_message: str | None = None,
    cf_scoring_result: CfScoringResult | None = None,
) -> str:
    """ドメイン層の出力生成ビルダーを呼び出す。"""
    base_output = build_fundamental_output_text(
        name=name,
        code4=code4,
        master=master,
        price=price,
        market_cap=market_cap,
        market_snapshot=market_snapshot,
        kabutan_forecast_pair=kabutan_forecast_pair,
    )
    output = build_kabutan_forecast_output(
        base_output,
        kabutan_forecast_pair,
        kabutan_source,
        kabutan_source_message,
        kabutan_cashflow_rows,
        market_cap,
        financial_metric_rows,
        quarterly_metric_rows,
        quarterly_message,
        cf_scoring_result,
    )
    if cf_scoring_result is None:
        return output
    return f"{output}\n{build_cf_scoring_summary_text(cf_scoring_result)}"
