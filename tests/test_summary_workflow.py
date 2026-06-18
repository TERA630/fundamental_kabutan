from datetime import date, datetime
from pathlib import Path

from app.data.file_cache import FileCache
from app.services.summary_workflow import (
    SummaryWorkflow,
    build_fundamental_summary_filename,
    build_technical_summary_filename,
)


def test_summary_filename_builders():
    assert build_fundamental_summary_filename(today=date(2026, 5, 30)) == "fundamental_summary-2026-05-30.md"
    assert build_technical_summary_filename(generated_at=datetime(2026, 5, 30, 14, 5)) == "technical_summary_05-30-14-05.md"


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
