import pytest

from app.domain.policies.range_table import RangeBand, RangeTable


def test_range_table_uses_descending_inclusive_lower_bounds_and_default():
    table = RangeTable(
        bands=(RangeBand(10, "high"), RangeBand(5, "medium")),
        default="low",
    )

    assert table.resolve(10) == "high"
    assert table.resolve(9.999) == "medium"
    assert table.resolve(5) == "medium"
    assert table.resolve(4.999) == "low"
    assert table.resolve(None) == "low"


def test_range_table_rejects_ascending_bands():
    with pytest.raises(ValueError, match="descending"):
        RangeTable(bands=(RangeBand(5, 1), RangeBand(10, 2)), default=0)
