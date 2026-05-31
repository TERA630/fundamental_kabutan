"""Plain-text builder for yFinance analyst estimates."""

from __future__ import annotations

from app.domain.models.analyst_estimates import AnalystEstimates, EpsRevisionPeriod


def _fmt_estimate_num(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:,.1f}"


def _fmt_estimate_count(value: int | None) -> str:
    if value is None:
        return "N/A"
    return str(value)


def _build_eps_revision_line(label: str, revision: EpsRevisionPeriod) -> str:
    return (
        f"{label}： 上方修正 {_fmt_estimate_count(revision.up_last_30_days)}人"
        f"　下方修正 {_fmt_estimate_count(revision.down_last_30_days)}人"
    )


def build_analyst_estimates_lines(estimates: AnalystEstimates | None) -> list[str]:
    estimates = estimates or AnalystEstimates.empty()
    return [
        "",
        "■アナリスト予想(yFinance)",
        f"アナリスト目標株価：{_fmt_estimate_num(estimates.target_mean_price)} 円 (アナリスト {_fmt_estimate_count(estimates.number_of_analyst_opinions)}人)",
        "EPS revisions (30日):",
        _build_eps_revision_line("今期末", estimates.current_year_eps_revisions),
        _build_eps_revision_line("来季末", estimates.next_year_eps_revisions),
    ]


__all__ = ["build_analyst_estimates_lines"]
