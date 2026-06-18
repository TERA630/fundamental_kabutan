from datetime import datetime

from app.services.analysis_output_workflow import AnalysisOutputWorkflow


def test_fetch_output_for_mode_technical_uses_technical_builder():
    calls = []
    workflow = AnalysisOutputWorkflow(
        fetch_technical_output=lambda **kwargs: calls.append(kwargs) or f"TECH:{kwargs['name']}:{kwargs['code4']}",
        fetch_analysis_output=lambda **_kwargs: "BAD",
        fetch_institutional_summary_text=lambda **_kwargs: "SUMMARY",
    )
    evaluation_at = datetime(2026, 5, 29, 9, 10)

    result = workflow.fetch_output_for_mode(
        name="トヨタ",
        code4="7203",
        mode="technical",
        evaluation_at=evaluation_at,
    )

    assert result.output == "TECH:トヨタ:7203"
    assert result.institutional_summary == "SUMMARY"
    assert calls == [{"name": "トヨタ", "code4": "7203", "evaluation_at": evaluation_at}]


def test_fetch_output_for_mode_fundamental_builds_output_without_cache_arguments():
    calls = []
    workflow = AnalysisOutputWorkflow(
        fetch_technical_output=lambda **_kwargs: "BAD",
        fetch_analysis_output=lambda **kwargs: calls.append(kwargs) or "FUND",
        fetch_institutional_summary_text=lambda **_kwargs: "SUMMARY",
    )

    result = workflow.fetch_output_for_mode(
        name="トヨタ",
        code4="7203",
        mode="fundamental",
    )

    assert result.output == "FUND"
    assert result.institutional_summary == "SUMMARY"
    assert calls == [{"name": "トヨタ", "code4": "7203", "kabutan_html_dir": None}]
