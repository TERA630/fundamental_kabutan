"""Domain input model for rankCF scoring."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CfScoringInput:
    code4: str
    as_of: str | None
    roic: float | None
    ocf: float | None
    net_income: float | None
    operating_income: float | None
    revenue: float | None
    fcf: float | None
    eps_cagr_3y: float | None
    sales_cagr_3y: float | None
    fcf_yield: float | None
    per: float | None


__all__ = ["CfScoringInput"]
