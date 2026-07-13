"""Builder for institutional summary panel text."""

from __future__ import annotations

from app.domain.models.institutional_summary import InstitutionalSummary

YEN_PER_OKU = 100_000_000


def build_institutional_summary_text(summary: InstitutionalSummary | None) -> str:
    if summary is None:
        return "機関投資サマリ\n時価総額：N/A\n流動性：N/A\n機関投資スコア：N/A"

    return "\n".join(
        [
            "機関投資サマリ",
            f"時価総額：{_fmt_oku(summary.market_cap_yen)}億円（{summary.market_cap_class or 'N/A'}）",
            f"流動性：出来高 {_fmt_volume(summary.volume)}（20日平均比 {_fmt_pct(summary.volume_vs_avg20_pct)}） 売買代金 {_fmt_oku(summary.trading_value_yen)}億円",
            f"機関投資スコア：{summary.score.total}/20点　Fundamental Score：{_fmt_score(summary.fundamental_score)}（{summary.fundamental_rank or 'N/A'}）",
        ]
    )


def _fmt_oku(value_yen: float | None) -> str:
    return "N/A" if value_yen is None else f"{value_yen / YEN_PER_OKU:,.1f}"


def _fmt_volume(value: float | None) -> str:
    return "N/A" if value is None else f"{value:,.0f}株"


def _fmt_pct(value: float | None) -> str:
    return "N/A" if value is None else f"{value:+.1f}%"


def _fmt_score(value: int | None) -> str:
    return "N/A" if value is None else f"{value}点"


__all__ = ["build_institutional_summary_text"]
