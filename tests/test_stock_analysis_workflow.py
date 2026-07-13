from app.data.file_cache import FileCache
from app.services import stock_analysis_workflow as stock_module
from app.services.stock_analysis_workflow import StockAnalysisWorkflow


class FundamentalService:
    def build_analysis_result(self, name, code4, *, kabutan_html_dir=None):
        return f"FUND:{name}:{code4}:{kabutan_html_dir}"


class TechnicalService:
    def build_analysis_result(self, *, name, code4):
        return {"name": name, "code4": code4}


def _workflow(tmp_path) -> StockAnalysisWorkflow:
    return StockAnalysisWorkflow(
        file_cache=FileCache(base_dir=tmp_path / "cache"),
        build_fundamental_service=lambda _cache: FundamentalService(),
        build_technical_service=lambda _cache: TechnicalService(),
        uses_default_fundamental_service=False,
        uses_default_technical_service=False,
        fetch_market_data_bundle=lambda _code4: None,
        build_fundamental_service_with_market_bundle=lambda _bundle: FundamentalService(),
    )


def test_fetch_analysis_output_builds_result_then_formats_it(tmp_path, monkeypatch):
    monkeypatch.setattr(stock_module, "build_fundamental_output_from_result", lambda result: result)

    output = _workflow(tmp_path).fetch_analysis_output(name="トヨタ", code4="7203")

    assert output == "FUND:トヨタ:7203:None"


def test_fetch_technical_output_builds_from_injected_service(tmp_path, monkeypatch):
    monkeypatch.setattr(stock_module, "build_technical_output", lambda result: f"TECH:{result['code4']}")

    assert _workflow(tmp_path).fetch_technical_output(name="トヨタ", code4="7203") == "TECH:7203"


def test_fetch_technical_output_result_returns_output_and_analysis_result(tmp_path, monkeypatch):
    monkeypatch.setattr(stock_module, "build_technical_output", lambda result: f"TECH:{result['code4']}")

    result = _workflow(tmp_path).fetch_technical_output_result(name="トヨタ", code4="7203")

    assert result.output == "TECH:7203"
    assert result.analysis_result == {"name": "トヨタ", "code4": "7203"}
