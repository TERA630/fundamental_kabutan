import pytest

from app.domain.builders.sector_breadth_output import build_single_stock_sector_breadth_text
from app.domain.models.sector_breadth import SectorBreadthRatio, SectorBreadthRow, SectorBreadthTable
from app.domain.models.technical_summary import TechnicalSummaryRow
from app.domain.models.watchlist import WatchlistEntry
from app.domain.policies.sector_breadth import (
    build_sector_breadth_table,
    classify_collapse_score_median,
    classify_sector_breadth,
    classify_terminal_position_median,
    classify_volume_vs_avg20_median,
    classify_vwap_above_ratio,
)


def _row(
    code4: str,
    *,
    latest: float | None = 100.0,
    vwap: float | None = 99.0,
    terminal: float | None = 0.7,
    dev25_pct: float | None = 1.0,
    collapse: int | None = 1,
    volume: float | None = 80.0,
    volume_spike_bearish: bool | None = False,
) -> TechnicalSummaryRow:
    return TechnicalSummaryRow(
        name=f"Stock{code4}",
        code4=code4,
        rank="A1",
        rank_label="位置良好",
        latest=latest,
        day_change_price=0.0,
        day_change_pct=0.0,
        three_session_change_pct=0.0,
        day_high=101.0,
        day_low=99.0,
        day_close_position=terminal,
        day_range_atr=1.0,
        vwap=vwap,
        vwap_diff_pct=None,
        dev25_pct=dev25_pct,
        ma25_distance_atr=1.0,
        volume_vs_avg20_pct=volume,
        previous_vwap_maintained=None,
        support_lines=(),
        resistance_lines=(),
        recent60_range_position=0.5,
        collapse_risk_score=collapse,
        volume_spike_bearish=volume_spike_bearish,
    )


def test_sector_breadth_indicator_labels_follow_boundaries():
    assert classify_vwap_above_ratio(0.70) == "セクター買い優勢"
    assert classify_vwap_above_ratio(0.50) == "中立〜やや強い"
    assert classify_vwap_above_ratio(0.30) == "まちまち"
    assert classify_vwap_above_ratio(0.29) == "セクター売り優勢"

    assert classify_terminal_position_median(0.70) == "高値圏維持、買い優勢"
    assert classify_terminal_position_median(0.50) == "反発中"
    assert classify_terminal_position_median(0.30) == "戻り鈍い"
    assert classify_terminal_position_median(0.29) == "売り圧優勢"

    assert classify_collapse_score_median(2.0) == "健全"
    assert classify_collapse_score_median(3.0) == "注意"
    assert classify_collapse_score_median(5.0) == "崩れ警戒"
    assert classify_collapse_score_median(7.0) == "回避"

    assert classify_volume_vs_avg20_median(80.0) == "実需あり"
    assert classify_volume_vs_avg20_median(50.0) == "普通"
    assert classify_volume_vs_avg20_median(30.0) == "薄い"
    assert classify_volume_vs_avg20_median(29.9) == "信頼度低い"


def test_classify_sector_breadth_prioritizes_breakdown_market():
    assert (
        classify_sector_breadth(
            vwap_above_ratio=0.25,
            terminal_position_median=0.30,
            ma25_above_ratio=0.90,
            collapse_score_median=5.0,
            volume_spike_bearish_count=1,
        )
        == "崩れ地合い"
    )
    assert (
        classify_sector_breadth(
            vwap_above_ratio=0.70,
            terminal_position_median=0.70,
            ma25_above_ratio=0.90,
            collapse_score_median=2.0,
        )
        == "強い上昇地合い"
    )
    assert (
        classify_sector_breadth(
            vwap_above_ratio=0.60,
            terminal_position_median=0.45,
            ma25_above_ratio=0.70,
            collapse_score_median=4.0,
        )
        == "押し目買い優勢"
    )
    assert (
        classify_sector_breadth(
            vwap_above_ratio=0.50,
            terminal_position_median=0.50,
            ma25_above_ratio=0.50,
            collapse_score_median=3.0,
        )
        == "まちまち"
    )
    assert (
        classify_sector_breadth(
            vwap_above_ratio=0.39,
            terminal_position_median=0.39,
            ma25_above_ratio=0.80,
            collapse_score_median=3.0,
        )
        == "戻り売り優勢"
    )
    assert (
        classify_sector_breadth(
            vwap_above_ratio=None,
            terminal_position_median=None,
            ma25_above_ratio=None,
            collapse_score_median=None,
        )
        == "まちまち"
    )


def test_build_sector_breadth_table_skips_tagless_entries_and_aggregates_by_sector():
    watchlist = (
        WatchlistEntry("A", "1001", ("半導体材料・装置",)),
        WatchlistEntry("B", "1002", ("半導体材料・装置", "水処理・環境インフラ")),
        WatchlistEntry("C", "1003", ()),
        WatchlistEntry("D", "1004", ("半導体材料・装置",)),
    )
    rows = (
        _row("1001", latest=105.0, vwap=100.0, terminal=0.80, dev25_pct=3.0, collapse=1, volume=90.0),
        _row("1002", latest=101.0, vwap=100.0, terminal=0.70, dev25_pct=1.0, collapse=2, volume=60.0),
        _row("1003", latest=80.0, vwap=100.0, terminal=0.10, dev25_pct=-10.0, collapse=6, volume=200.0),
        _row("1004", latest=98.0, vwap=100.0, terminal=0.60, dev25_pct=0.5, collapse=3, volume=50.0),
    )

    table = build_sector_breadth_table(rows=rows, watchlist_entries=watchlist)

    semiconductor = table.rows[0]
    assert semiconductor.sector == "半導体材料・装置"
    assert semiconductor.judgement == "押し目買い優勢"
    assert semiconductor.vwap_above.count == 2
    assert semiconductor.vwap_above.total == 3
    assert semiconductor.vwap_above.ratio == pytest.approx(2 / 3)
    assert semiconductor.terminal_position_median == pytest.approx(0.70)
    assert semiconductor.ma25_above.count == 3
    assert semiconductor.ma25_above.total == 3
    assert semiconductor.collapse_score_median == pytest.approx(2.0)
    assert semiconductor.volume_vs_avg20_median_pct == pytest.approx(60.0)
    assert "中立〜やや強い" in semiconductor.comment

    water = table.rows[1]
    assert water.sector == "水処理・環境インフラ"
    assert water.vwap_above.count == 1
    assert water.vwap_above.total == 1


def test_build_sector_breadth_table_uses_available_denominators_per_metric():
    watchlist = (
        WatchlistEntry("A", "1001", ("商社・資源",)),
        WatchlistEntry("B", "1002", ("商社・資源",)),
    )
    rows = (
        _row("1001", latest=None, vwap=100.0, terminal=None, dev25_pct=None, collapse=None, volume=None),
        _row("1002", latest=90.0, vwap=100.0, terminal=0.20, dev25_pct=-1.0, collapse=6, volume=120.0, volume_spike_bearish=True),
    )

    row = build_sector_breadth_table(rows=rows, watchlist_entries=watchlist).rows[0]

    assert row.vwap_above.count == 0
    assert row.vwap_above.total == 1
    assert row.terminal_position_median == pytest.approx(0.20)
    assert row.ma25_above.count == 0
    assert row.ma25_above.total == 1
    assert row.collapse_score_median == pytest.approx(6.0)
    assert row.volume_vs_avg20_median_pct == pytest.approx(120.0)
    assert row.volume_spike_bearish_count == 1
    assert row.judgement == "崩れ地合い"
    assert "対象2銘柄" in row.comment
    assert "出来高増下落1銘柄" in row.comment


def test_build_sector_breadth_comment_marks_single_stock_sector():
    watchlist = (WatchlistEntry("A", "1001", ("水処理・環境インフラ",)),)
    rows = (_row("1001"),)

    row = build_sector_breadth_table(rows=rows, watchlist_entries=watchlist).rows[0]

    assert row.comment.endswith("対象1銘柄のみ")


def test_build_single_stock_sector_breadth_text_formats_selected_sectors_only():
    table = SectorBreadthTable(
        rows=(
            SectorBreadthRow(
                sector="半導体材料・装置",
                judgement="押し目買い優勢",
                vwap_above=SectorBreadthRatio(count=2, total=3, ratio=2 / 3),
                terminal_position_median=0.65,
                ma25_above=SectorBreadthRatio(count=3, total=3, ratio=1.0),
                collapse_score_median=2.0,
                volume_vs_avg20_median_pct=68.0,
                volume_spike_bearish_count=0,
                comment="中立〜やや強い / 反発中",
            ),
            SectorBreadthRow(
                sector="商社・資源",
                judgement="まちまち",
                vwap_above=SectorBreadthRatio(count=1, total=2, ratio=0.5),
                terminal_position_median=0.50,
                ma25_above=SectorBreadthRatio(count=1, total=2, ratio=0.5),
                collapse_score_median=3.0,
                volume_vs_avg20_median_pct=40.0,
                volume_spike_bearish_count=0,
                comment="まちまち",
            ),
        )
    )

    text = build_single_stock_sector_breadth_text(table, ("半導体材料・装置",))

    assert text.startswith("■セクター地合\n半導体材料・装置：押し目買い優勢")
    assert "VWAP上 2/3 67%" in text
    assert "終端中央値 65%" in text
    assert "商社・資源" not in text
