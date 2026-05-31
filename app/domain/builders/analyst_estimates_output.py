"""Plain-text builder for yFinance analyst estimates."""

from __future__ import annotations

from app.domain.models.analyst_estimates import AnalystEstimates, EpsRevisionPeriod


def _fmt_estimate_num(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.0f}"


def _fmt_estimate_count(value: int | None) -> str:
    if value is None:
        return "N/A"
    return str(value)


def _fmt_gap_pct(*, target_mean_price: float | None, price: float | None) -> str:
    if target_mean_price is None or price is None or price == 0:
        return "N/A"
    return f"{((target_mean_price - price) / price) * 100:+.1f}%"


def _build_eps_revision_line(label: str, revision: EpsRevisionPeriod) -> str:
    return f"{label}EPS修正 ↑{_fmt_estimate_count(revision.up_last_30_days)} ↓{_fmt_estimate_count(revision.down_last_30_days)}"


def build_analyst_estimates_lines(estimates: AnalystEstimates | None, *, price: float | None = None) -> list[str]:
    estimates = estimates or AnalystEstimates.empty()
    return [
        "",
        "■アナリスト",
        f"目標株価 {_fmt_estimate_num(estimates.target_mean_price)}円(現価格との乖離{_fmt_gap_pct(target_mean_price=estimates.target_mean_price, price=price)}：アナリスト{_fmt_estimate_count(estimates.number_of_analyst_opinions)}人)",
        _build_eps_revision_line("今期", estimates.current_year_eps_revisions),
        _build_eps_revision_line("来季", estimates.next_year_eps_revisions),
    ]


__all__ = ["build_analyst_estimates_lines"]
