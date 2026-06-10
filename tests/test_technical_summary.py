from types import SimpleNamespace

from app.domain.builders.technical_summary import build_technical_summary_markdown
from app.domain.models.technical_summary import TechnicalSummaryLine, TechnicalSummaryTable
from app.domain.policies.technical_summary import (
    build_nearby_resistance_lines,
    build_nearby_support_lines,
    classify_technical_summary_rank,
)
from app.domain.usecases.technical_summary import TechnicalSummaryService


def test_classify_technical_summary_rank_uses_focus_theme_thresholds():
    assert classify_technical_summary_rank(dev25_pct=4.5, latest=105, vwap=100, focus_theme=True) == "A2"
    assert classify_technical_summary_rank(dev25_pct=7.5, latest=95, vwap=100, focus_theme=True) == "B1"
    assert classify_technical_summary_rank(dev25_pct=7.5, latest=105, vwap=100, focus_theme=False) == "A2"
    assert classify_technical_summary_rank(dev25_pct=8.5, latest=95, vwap=100, focus_theme=False) == "B1"


def test_classify_technical_summary_rank_covers_c_and_e_cases():
    assert classify_technical_summary_rank(dev25_pct=3.0, latest=95, vwap=100, focus_theme=False) == "C1"
    assert classify_technical_summary_rank(dev25_pct=-3.0, latest=105, vwap=100, focus_theme=False) == "C2"
    assert classify_technical_summary_rank(dev25_pct=-3.0, latest=95, vwap=100, focus_theme=False) == "E"


def test_build_nearby_support_and_resistance_lines_select_two_nearest():
    support = build_nearby_support_lines(
        latest=100,
        ma25=98,
        previous_low=94,
        recent20_low=97,
        ma75=90,
        recent60_low=80,
    )
    resistance = build_nearby_resistance_lines(
        latest=100,
        previous_high=103,
        recent20_high=110,
        recent60_high=105,
        ma25=98,
    )

    assert support == (TechnicalSummaryLine("25ME", 98), TechnicalSummaryLine("20D-L", 97))
    assert resistance == (TechnicalSummaryLine("PrevH", 103), TechnicalSummaryLine("60D-H", 105))


def test_technical_summary_service_builds_row_and_markdown():
    result = SimpleNamespace(
        name="AIテスト",
        code4="1234",
        snapshot=SimpleNamespace(
            price=SimpleNamespace(
                latest=105.0,
                high=108.0,
                low=100.0,
                day_change_price=2.0,
                day_change_pct=1.94,
                volume=1200.0,
                volume_avg20=1000.0,
            ),
            moving_average=SimpleNamespace(
                ma25=101.0,
                ma75=95.0,
                ma25_prev5=101.0,
                dev25_pct=3.96,
                ma25_distance_atr=0.8,
            ),
            range=SimpleNamespace(day_range_atr=1.1),
            previous_session=SimpleNamespace(prev_low=99.0, prev_high=109.0),
            breakline=SimpleNamespace(
                recent20_low=97.0,
                recent60_low=90.0,
                recent20_high=112.0,
                recent60_high=120.0,
                recent60_range_position=0.75,
            ),
        ),
        vwap_snapshot={"vwap": 102.0},
        previous_intraday_snapshot={"prev_am_vwap_maintained": True, "prev_pm_vwap_maintained": False},
        three_session_momentum=SimpleNamespace(change_pct=-2.5),
    )
    service = TechnicalSummaryService(lambda _name, _code4: result)

    table = service.build_summary_table([("AIテスト", "1234")])
    markdown = build_technical_summary_markdown(table)

    assert isinstance(table, TechnicalSummaryTable)
    assert table.rows[0].rank == "A1"
    assert table.rows[0].previous_vwap_maintained is False
    assert "## A1 位置良好" in markdown
    assert "25ME dev" in markdown
    assert "102円(+2.9%)" in markdown
    assert "AIテスト(1234)" in markdown
