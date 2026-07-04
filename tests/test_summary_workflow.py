from datetime import date, datetime
from pathlib import Path

from app.data.file_cache import FileCache
from app.domain.models.sector_breadth import SectorBreadthRatio, SectorBreadthRow, SectorBreadthTable
from app.domain.models.technical_summary import TechnicalSummaryTable
from app.domain.models.watchlist import WatchlistEntry
from app.services.summary_workflow import (
    SummaryWorkflow,
    build_fundamental_summary_filename,
    build_hybrid_summary_filename,
    build_technical_summary_filename,
)


def test_summary_filename_builders():
    assert build_fundamental_summary_filename(today=date(2026, 5, 30)) == "fundamental_summary-2026-05-30.md"
    assert build_technical_summary_filename(generated_at=datetime(2026, 5, 30, 14, 5)) == "technical_summary_05-30-14-05.md"
    assert build_hybrid_summary_filename(generated_at=datetime(2026, 5, 30, 14, 5)) == "hybrid_summary_05-30-14-05.md"


def test_build_summary_table_for_mode_dispatches(monkeypatch, tmp_path: Path):
    class DummyFundamentalSummaryService:
        def __init__(self, service):
            self.service = service

        def build_summary_table(self, watchlist_entries, *, kabutan_html_dir=None):
            assert watchlist_entries == [("トヨタ", "7203")]
            assert kabutan_html_dir == tmp_path / "html"
            return "FUND_TABLE"

    class DummyTechnicalSummaryService:
        def __init__(self, build_result, build_us_market_summary=None):
            self.build_result = build_result
            self.build_us_market_summary = build_us_market_summary

        def build_summary_table(self, watchlist_entries):
            assert watchlist_entries == [("トヨタ", "7203")]
            return "TECH_TABLE"

    monkeypatch.setattr("app.services.summary_workflow.FundamentalSummaryService", DummyFundamentalSummaryService)
    monkeypatch.setattr("app.services.summary_workflow.TechnicalSummaryService", DummyTechnicalSummaryService)
    workflow = SummaryWorkflow(
        file_cache=FileCache(base_dir=tmp_path / "cache"),
        build_fundamental_service=lambda _cache: object(),
        build_technical_summary_result=lambda _name, _code4: object(),
    )

    fund = workflow.build_summary_table_for_mode(
        mode="fundamental",
        watchlist_entries=[("トヨタ", "7203")],
        kabutan_html_dir=tmp_path / "html",
    )
    tech = workflow.build_summary_table_for_mode(
        mode="technical",
        watchlist_entries=[("トヨタ", "7203")],
        kabutan_html_dir=tmp_path / "html",
    )

    assert fund == "FUND_TABLE"
    assert tech == "TECH_TABLE"


def test_build_and_save_technical_summary_passes_evaluation_at(monkeypatch, tmp_path: Path):
    calls = []

    class DummyTechnicalSummaryService:
        def __init__(self, build_result, build_us_market_summary=None):
            self.build_result = build_result
            self.build_us_market_summary = build_us_market_summary

        def build_summary_table(self, watchlist_entries):
            assert watchlist_entries == [("トヨタ", "7203")]
            self.build_result("トヨタ", "7203")
            return "TECH_TABLE"

    monkeypatch.setattr("app.services.summary_workflow.TechnicalSummaryService", DummyTechnicalSummaryService)
    monkeypatch.setattr("app.services.summary_workflow.build_technical_summary_markdown", lambda table: f"TECH:{table}\n")
    evaluation_at = datetime(2026, 5, 29, 9, 10)
    workflow = SummaryWorkflow(
        file_cache=FileCache(base_dir=tmp_path / "cache"),
        build_fundamental_service=lambda _cache: object(),
        build_technical_summary_result=lambda name, code4, *, evaluation_at=None: calls.append(
            (name, code4, evaluation_at)
        ) or object(),
    )

    output = workflow.build_and_save_technical_summary(
        watchlist_entries=[("トヨタ", "7203")],
        output_dir=tmp_path,
        generated_at=datetime(2026, 5, 29, 9, 20),
        evaluation_at=evaluation_at,
    )

    assert calls == [("トヨタ", "7203", evaluation_at)]
    assert output.read_text(encoding="utf-8") == "TECH:TECH_TABLE\n"


def test_build_technical_sector_breadth_output_formats_selected_stock_sector(monkeypatch, tmp_path: Path):
    calls = []

    class DummyTechnicalSummaryService:
        def __init__(self, build_result, build_us_market_summary=None):
            self.build_result = build_result

        def build_summary_table(self, watchlist_entries):
            assert watchlist_entries == [
                WatchlistEntry("SemiA", "1001", ("半導体材料・装置",)),
                WatchlistEntry("SemiB", "1003", ("半導体材料・装置",)),
                WatchlistEntry("Multi", "1005", ("半導体材料・装置",)),
            ]
            for entry in watchlist_entries:
                self.build_result(entry.name, entry.code4)
            return TechnicalSummaryTable(
                rows=(),
                sector_breadth=SectorBreadthTable(
                    rows=(
                        SectorBreadthRow(
                            sector="半導体材料・装置",
                            judgement="強い上昇地合い",
                            vwap_above=SectorBreadthRatio(count=3, total=4, ratio=0.75),
                            terminal_position_median=0.72,
                            ma25_above=SectorBreadthRatio(count=4, total=4, ratio=1.0),
                            collapse_score_median=1.0,
                            volume_vs_avg20_median_pct=63.0,
                            volume_spike_bearish_count=0,
                            comment="セクター買い優勢",
                        ),
                    ),
                ),
            )

    monkeypatch.setattr("app.services.summary_workflow.TechnicalSummaryService", DummyTechnicalSummaryService)
    evaluation_at = datetime(2026, 5, 29, 9, 10)
    workflow = SummaryWorkflow(
        file_cache=FileCache(base_dir=tmp_path / "cache"),
        build_fundamental_service=lambda _cache: object(),
        build_technical_summary_result=lambda name, code4, *, evaluation_at=None: calls.append(
            (name, code4, evaluation_at)
        ) or object(),
    )

    text = workflow.build_technical_sector_breadth_output(
        watchlist_entries=[
            WatchlistEntry("SemiA", "1001", ("半導体材料・装置",)),
            WatchlistEntry("Tagless", "1002"),
            WatchlistEntry("SemiB", "1003", ("半導体材料・装置",)),
            WatchlistEntry("Trading", "1004", ("商社・資源",)),
            WatchlistEntry("Multi", "1005", ("半導体材料・装置", "商社・資源")),
        ],
        code4="1001",
        evaluation_at=evaluation_at,
    )

    assert calls == [
        ("SemiA", "1001", evaluation_at),
        ("SemiB", "1003", evaluation_at),
        ("Multi", "1005", evaluation_at),
    ]
    assert "■セクター地合" in text
    assert "半導体材料・装置：強い上昇地合い" in text


def test_build_technical_sector_breadth_output_reuses_prebuilt_selected_result(monkeypatch, tmp_path: Path):
    calls = []
    selected_result = object()

    class DummyTechnicalSummaryService:
        def __init__(self, build_result, build_us_market_summary=None):
            self.build_result = build_result

        def build_summary_table(self, watchlist_entries):
            for entry in watchlist_entries:
                result = self.build_result(entry.name, entry.code4)
                if entry.code4 == "1001":
                    assert result is selected_result
            return TechnicalSummaryTable(
                rows=(),
                sector_breadth=SectorBreadthTable(
                    rows=(
                        SectorBreadthRow(
                            sector="半導体材料・装置",
                            judgement="まちまち",
                            vwap_above=SectorBreadthRatio(count=1, total=2, ratio=0.5),
                            terminal_position_median=0.50,
                            ma25_above=SectorBreadthRatio(count=2, total=2, ratio=1.0),
                            collapse_score_median=2.0,
                            volume_vs_avg20_median_pct=60.0,
                            volume_spike_bearish_count=0,
                            comment="まちまち",
                        ),
                    ),
                ),
            )

    monkeypatch.setattr("app.services.summary_workflow.TechnicalSummaryService", DummyTechnicalSummaryService)
    workflow = SummaryWorkflow(
        file_cache=FileCache(base_dir=tmp_path / "cache"),
        build_fundamental_service=lambda _cache: object(),
        build_technical_summary_result=lambda name, code4, *, evaluation_at=None: calls.append(
            (name, code4, evaluation_at)
        ) or object(),
    )

    workflow.build_technical_sector_breadth_output(
        watchlist_entries=[
            WatchlistEntry("SemiA", "1001", ("半導体材料・装置",)),
            WatchlistEntry("SemiB", "1003", ("半導体材料・装置",)),
        ],
        code4="1001",
        evaluation_at=datetime(2026, 5, 29, 9, 10),
        prebuilt_results={"1001": selected_result},
    )

    assert calls == [("SemiB", "1003", datetime(2026, 5, 29, 9, 10))]


def test_build_technical_sector_breadth_output_skips_tagless_stock(tmp_path: Path):
    workflow = SummaryWorkflow(
        file_cache=FileCache(base_dir=tmp_path / "cache"),
        build_fundamental_service=lambda _cache: object(),
        build_technical_summary_result=lambda _name, _code4: object(),
    )

    assert (
        workflow.build_technical_sector_breadth_output(
            watchlist_entries=[("トヨタ", "7203")],
            code4="7203",
        )
        == ""
    )


def test_build_and_save_hybrid_summary_merges_existing_summary_tables(monkeypatch, tmp_path: Path):
    class DummyFundamentalSummaryService:
        def __init__(self, service):
            self.service = service

        def build_summary_table(self, watchlist_entries, *, kabutan_html_dir=None):
            assert watchlist_entries == [("トヨタ", "7203")]
            assert kabutan_html_dir == tmp_path / "html"
            return "FUND_TABLE"

    class DummyTechnicalSummaryService:
        def __init__(self, build_result, build_us_market_summary=None):
            self.build_result = build_result

        def build_summary_table(self, watchlist_entries):
            assert watchlist_entries == [("トヨタ", "7203")]
            self.build_result("トヨタ", "7203")
            return "TECH_TABLE"

    class DummyHybridSummaryService:
        def build_summary_table(self, *, fundamental_table, technical_table):
            assert fundamental_table == "FUND_TABLE"
            assert technical_table == "TECH_TABLE"
            return "HYBRID_TABLE"

    calls = []
    monkeypatch.setattr("app.services.summary_workflow.FundamentalSummaryService", DummyFundamentalSummaryService)
    monkeypatch.setattr("app.services.summary_workflow.TechnicalSummaryService", DummyTechnicalSummaryService)
    monkeypatch.setattr("app.services.summary_workflow.HybridSummaryService", DummyHybridSummaryService)
    monkeypatch.setattr("app.services.summary_workflow.build_hybrid_summary_markdown", lambda table: f"HYBRID:{table}\n")
    evaluation_at = datetime(2026, 5, 29, 9, 10)
    workflow = SummaryWorkflow(
        file_cache=FileCache(base_dir=tmp_path / "cache"),
        build_fundamental_service=lambda _cache: object(),
        build_technical_summary_result=lambda name, code4, *, evaluation_at=None: calls.append(
            (name, code4, evaluation_at)
        ) or object(),
    )

    output = workflow.build_and_save_hybrid_summary(
        watchlist_entries=[("トヨタ", "7203")],
        output_dir=tmp_path,
        kabutan_html_dir=tmp_path / "html",
        generated_at=datetime(2026, 5, 29, 9, 20),
        evaluation_at=evaluation_at,
    )

    assert output == tmp_path / "hybrid_summary_05-29-09-20.md"
    assert calls == [("トヨタ", "7203", evaluation_at)]
    assert output.read_text(encoding="utf-8") == "HYBRID:HYBRID_TABLE\n"
