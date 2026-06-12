from app.services.analysis_output_workflow import AnalysisOutputWorkflow


def test_fetch_output_for_mode_technical_skips_output_cache_save():
    calls = {"saved": 0}
    workflow = AnalysisOutputWorkflow(
        fetch_technical_output=lambda *, name, code4: f"TECH:{name}:{code4}",
        fetch_analysis_output=lambda **_kwargs: "BAD",
        save_output_cache_for_today=lambda _cache: calls.__setitem__("saved", calls["saved"] + 1),
        fetch_institutional_summary_text=lambda **_kwargs: "SUMMARY",
    )

    result = workflow.fetch_output_for_mode(
        name="トヨタ",
        code4="7203",
        mode="technical",
        output_cache={},
    )

    assert result.output == "TECH:トヨタ:7203"
    assert result.institutional_summary == "SUMMARY"
    assert calls["saved"] == 0


def test_fetch_output_for_mode_fundamental_saves_output_cache():
    calls = {"saved": 0, "cache_key": None}

    def fetch_analysis_output(**kwargs):
        calls["cache_key"] = kwargs["output_cache_key"]
        kwargs["output_cache"][kwargs["output_cache_key"]] = "FUND"
        return "FUND"

    workflow = AnalysisOutputWorkflow(
        fetch_technical_output=lambda **_kwargs: "BAD",
        fetch_analysis_output=fetch_analysis_output,
        save_output_cache_for_today=lambda _cache: calls.__setitem__("saved", calls["saved"] + 1),
        fetch_institutional_summary_text=lambda **_kwargs: "SUMMARY",
    )
    output_cache = {}

    result = workflow.fetch_output_for_mode(
        name="トヨタ",
        code4="7203",
        mode="fundamental",
        output_cache=output_cache,
        output_cache_key="7203|-",
    )

    assert result.output == "FUND"
    assert result.institutional_summary == "SUMMARY"
    assert output_cache == {"7203|-": "FUND"}
    assert calls == {"saved": 1, "cache_key": "7203|-"}
