"""Domain policy for valuation labels used in the opening summary."""

from __future__ import annotations

from typing import Literal


PerIndustryGroup = Literal["低PER許容業種", "通常/成長業種"]
PerLevel = Literal["割安PER", "適正PER", "高PER", "超高PER"]
RoicLevel = Literal["低収益ROIC", "低ROIC", "良好ROIC", "高ROIC", "超高ROIC"]


LOW_PER_INDUSTRY_KEYWORDS = (
    "商社",
    "卸売",
    "trading",
    "conglomerate",
    "bank",
    "banks",
    "銀行",
    "financial services",
    "telecom",
    "telecommunication",
    "通信",
)


def classify_per_industry_group(industry: str | None) -> PerIndustryGroup:
    if not industry:
        return "通常/成長業種"
    normalized = industry.strip().lower()
    if any(keyword in normalized for keyword in LOW_PER_INDUSTRY_KEYWORDS):
        return "低PER許容業種"
    return "通常/成長業種"


def classify_per_level(per: float | int | None, industry: str | None = None) -> PerLevel | None:
    if per is None:
        return None
    per_value = float(per)
    if per_value <= 0:
        return None

    group = classify_per_industry_group(industry)
    if group == "低PER許容業種":
        if per_value < 8:
            return "割安PER"
        if per_value < 15:
            return "適正PER"
        if per_value <= 25:
            return "高PER"
        return "超高PER"

    if per_value < 15:
        return "割安PER"
    if per_value < 30:
        return "適正PER"
    if per_value <= 50:
        return "高PER"
    return "超高PER"


def classify_roic_level(roic: float | int | None) -> RoicLevel | None:
    if roic is None:
        return None
    roic_value = float(roic)
    if roic_value > 20:
        return "超高ROIC"
    if roic_value >= 12:
        return "高ROIC"
    if roic_value >= 7:
        return "良好ROIC"
    if roic_value >= 3:
        return "低ROIC"
    return "低収益ROIC"


__all__ = [
    "PerIndustryGroup",
    "PerLevel",
    "RoicLevel",
    "classify_per_industry_group",
    "classify_per_level",
    "classify_roic_level",
]
