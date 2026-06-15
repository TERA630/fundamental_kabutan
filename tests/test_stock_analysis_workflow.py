from app.data.file_cache import FileCache
from app.services import stock_analysis_workflow as stock_module
from app.services.stock_analysis_workflow import StockAnalysisWorkflow


class LegacyFundamentalService:
    def build_analysis_output(self, name, code4, *, build_output_fn, kabutan_html_dir=None):
        return f"FUND:{name}:{code4}:{kabutan_html_dir}"


class TechnicalService:
    def build_analysis_result(self, *, name, code4):
        return {"name": name, "code4": code4}


def test_fetch_analysis_output_uses_cache_before_building_service(tmp_path):
    calls = {"fundamental": 0}

    def build_fundamental_service(_file_cache):
        calls["fundamental"] += 1
        return LegacyFundamentalService()

    workflow = StockAnalysisWorkflow(
        file_cache=FileCache(base_dir=tmp_path / "cache"),
        build_fundamental_service=build_fundamental_service,
        build_technical_service=lambda _file_cache: TechnicalService(),
        uses_default_fundamental_service=False,
        uses_default_technical_service=False,
        fetch_market_data_bundle=lambda _code4: None,
        build_fundamental_service_with_market_bundle=lambda _bundle: LegacyFundamentalService(),
    )
    output_cache = {"7203|cached": "CACHED"}

    assert (
        workflow.fetch_analysis_output(
            name="トヨタ",
            code4="7203",
            output_cache=output_cache,
            output_cache_key="7203|cached",
        )
        == "CACHED"
    )
    assert calls["fundamental"] == 0


def test_fetch_technical_output_builds_from_injected_service(tmp_path, monkeypatch):
    monkeypatch.setattr(stock_module, "build_technical_output", lambda result: f"TECH:{result['code4']}")
    workflow = StockAnalysisWorkflow(
        file_cache=FileCache(base_dir=tmp_path / "cache"),
        build_fundamental_service=lambda _file_cache: LegacyFundamentalService(),
        build_technical_service=lambda _file_cache: TechnicalService(),
        uses_default_fundamental_service=False,
        uses_default_technical_service=False,
        fetch_market_data_bundle=lambda _code4: None,
        build_fundamental_service_with_market_bundle=lambda _bundle: LegacyFundamentalService(),
    )

    assert workflow.fetch_technical_output(name="トヨタ", code4="7203") == "TECH:7203"
