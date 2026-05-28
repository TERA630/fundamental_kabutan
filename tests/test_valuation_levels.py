import pytest

from app.domain.policies.valuation_levels import (
    classify_per_industry_group,
    classify_per_level,
    classify_roic_level,
)


@pytest.mark.parametrize(
    ("industry", "expected"),
    [
        ("銀行業", "低PER許容業種"),
        ("Banks - Regional", "低PER許容業種"),
        ("Telecom Services", "低PER許容業種"),
        ("総合商社", "低PER許容業種"),
        ("Semiconductors", "通常/成長業種"),
        ("Industrials", "通常/成長業種"),
        (None, "通常/成長業種"),
    ],
)
def test_classify_per_industry_group(industry, expected):
    assert classify_per_industry_group(industry) == expected


@pytest.mark.parametrize(
    ("per", "expected"),
    [
        (7.9, "割安PER"),
        (8.0, "適正PER"),
        (14.9, "適正PER"),
        (15.0, "高PER"),
        (25.0, "高PER"),
        (25.1, "超高PER"),
    ],
)
def test_classify_per_level_for_low_per_tolerant_industry(per, expected):
    assert classify_per_level(per, "Banks") == expected


@pytest.mark.parametrize(
    ("per", "expected"),
    [
        (14.9, "割安PER"),
        (15.0, "適正PER"),
        (29.9, "適正PER"),
        (30.0, "高PER"),
        (50.0, "高PER"),
        (50.1, "超高PER"),
    ],
)
def test_classify_per_level_for_normal_growth_industry(per, expected):
    assert classify_per_level(per, "Semiconductors") == expected


def test_classify_per_level_returns_none_for_missing_or_invalid_per():
    assert classify_per_level(None, "Banks") is None
    assert classify_per_level(0, "Banks") is None
    assert classify_per_level(-1, "Banks") is None


@pytest.mark.parametrize(
    ("roic", "expected"),
    [
        (20.1, "超高ROIC"),
        (20.0, "高ROIC"),
        (12.0, "高ROIC"),
        (11.9, "良好ROIC"),
        (7.0, "良好ROIC"),
        (6.9, "低ROIC"),
        (3.0, "低ROIC"),
        (2.9, "低収益ROIC"),
    ],
)
def test_classify_roic_level(roic, expected):
    assert classify_roic_level(roic) == expected


def test_classify_roic_level_returns_none_for_missing_roic():
    assert classify_roic_level(None) is None
