from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
import zipfile

import pytest

from app.web import WebUiState, build_copy_text, create_app, parse_uploaded_watchlist, resolve_existing_dir


def test_parse_uploaded_watchlist_supports_cp932_bytes():
    data = "トヨタ (7203)\n任天堂,7974\n".encode("cp932")

    entries = parse_uploaded_watchlist(data)

    assert entries == [("トヨタ", "7203"), ("任天堂", "7974")]


def test_build_copy_text_includes_institutional_summary_panel():
    text = build_copy_text("機関投資サマリ\n時価総額：N/A", "本文")

    assert text == "機関投資サマリ\n時価総額：N/A\n\n本文"


def test_resolve_existing_dir_accepts_container_path(tmp_path: Path):
    resolved = resolve_existing_dir(str(tmp_path))

    assert resolved == tmp_path.resolve()


def test_resolve_existing_dir_rejects_missing_path(tmp_path: Path):
    with pytest.raises(ValueError, match="株探HTMLフォルダが見つかりません"):
        resolve_existing_dir(str(tmp_path / "missing"))


def test_index_uses_html_output_panel_without_visible_textarea():
    state = WebUiState()
    state.mode = "fundamental"
    state.output = """■四半期トレンド
　　　売上|営業利益率|昨年同期比|修正一株益
2025.3　10.0億|10.0%|-10%|10.0円
"""
    client = create_app(state).test_client()

    html = client.get("/").data.decode("utf-8")

    assert '<div class="rich-output">' in html
    assert '<table class="fundamental-table">' in html
    assert '<textarea readonly' not in html
    assert '<textarea id="copy-source"' in html


def test_index_renders_technical_output_as_pre_text_not_visible_textarea():
    state = WebUiState()
    state.mode = "technical"
    state.output = "Technical output"
    client = create_app(state).test_client()

    html = client.get("/").data.decode("utf-8")

    assert '<pre class="text-block">Technical output</pre>' in html
    assert '<textarea readonly' not in html
    assert '<button id="summary-button" formaction="/summary" type="submit">サマリ表示</button>' in html


def test_technical_summary_post_renders_summary_html_without_kabutan_dir(monkeypatch):
    class FakeController:
        def fetch_output_cache_for_today(self):
            return {}

        def fetch_resolved_watchlist_path(self):
            return SimpleNamespace(status="missing", file_path=None)

        def fetch_resolved_kabutan_html_dir(self):
            return SimpleNamespace(status="missing", dir_path=None)

        def build_technical_summary_table(self, *, watchlist_entries):
            assert watchlist_entries == [("トヨタ", "7203")]
            return "TECH_TABLE"

    monkeypatch.setattr("app.web.build_technical_summary_html", lambda table: f"<section>{table}</section>")

    state = WebUiState(controller=FakeController())
    state.mode = "technical"
    state.watchlist = [("トヨタ", "7203")]
    client = create_app(state).test_client()

    html = client.post(
        "/summary",
        data={"selected_stock": "トヨタ (7203)", "mode": "technical"},
    ).data.decode("utf-8")

    assert "<section>TECH_TABLE</section>" in html
    assert state.fundamental_summary_html == "<section>TECH_TABLE</section>"
    assert state.status == "Technicalサマリを表示しました。"


def test_index_copy_button_has_textarea_fallback_for_insecure_contexts():
    state = WebUiState()
    state.mode = "fundamental"
    state.output = "Fundamental output"
    client = create_app(state).test_client()

    html = client.get("/").data.decode("utf-8")

    assert "window.isSecureContext" in html
    assert "copyWithTextareaFallback" in html
    assert 'document.execCommand("copy")' in html


def test_index_has_kabutan_html_folder_picker():
    state = WebUiState()
    client = create_app(state).test_client()

    html = client.get("/").data.decode("utf-8")

    assert 'name="kabutan_html_files"' in html
    assert "webkitdirectory" in html
    assert 'enctype="multipart/form-data"' in html
    assert 'form action="/kabutan-package"' not in html
    assert "HTMLを正規化してZip作成" not in html
    assert 'form action="/kabutan-package/import"' in html
    assert 'name="kabutan_package_zip"' in html
    assert "Uploaded package" in html
    assert "Zipをアップロード" in html


def test_set_kabutan_dir_accepts_uploaded_html_folder(tmp_path: Path):
    class FakeController:
        def __init__(self):
            self.file_cache = SimpleNamespace(base_dir=tmp_path)
            self.saved_dir = None
            self.cleared_zip = False

        def fetch_output_cache_for_today(self):
            return {}

        def fetch_resolved_watchlist_path(self):
            return SimpleNamespace(status="missing", file_path=None)

        def fetch_resolved_kabutan_html_dir(self):
            return SimpleNamespace(status="missing", dir_path=None)

        def save_kabutan_html_dir_cache(self, path):
            self.saved_dir = path

        def clear_kabutan_package_zip_cache(self):
            self.cleared_zip = True

    controller = FakeController()
    state = WebUiState(controller=controller)
    client = create_app(state).test_client()
    state.kabutan_package_zip_path = tmp_path / "package.zip"
    state.kabutan_package_zip_signature = (1, 2)

    html = client.post(
        "/kabutan-dir",
        data={
            "kabutan_html_files": [
                (BytesIO(b"<html>7203</html>"), "kabutan_html/7203.html"),
                (BytesIO(b"<html>7974</html>"), "kabutan_html/7974.htm"),
                (BytesIO(b"not html"), "kabutan_html/readme.txt"),
            ],
        },
        content_type="multipart/form-data",
    ).data.decode("utf-8")

    assert state.kabutan_html_dir == (tmp_path / "web_uploaded_kabutan_html").resolve()
    assert state.kabutan_package_zip_path is None
    assert state.kabutan_package_zip_signature is None
    assert controller.saved_dir == state.kabutan_html_dir
    assert controller.cleared_zip is True
    assert (state.kabutan_html_dir / "7203.html").read_bytes() == b"<html>7203</html>"
    assert (state.kabutan_html_dir / "7974.htm").read_bytes() == b"<html>7974</html>"
    assert not (state.kabutan_html_dir / "readme.txt").exists()
    assert "株探HTMLフォルダを設定しました" in html


def test_upload_kabutan_package_zip_keeps_zip_without_extracting(tmp_path: Path):
    class FakeController:
        def __init__(self):
            self.file_cache = SimpleNamespace(base_dir=tmp_path)
            self.saved_zip = None
            self.inspected_zip = None
            self.import_called = False

        def fetch_output_cache_for_today(self):
            return {"7203|-": "cached"}

        def fetch_resolved_watchlist_path(self):
            return SimpleNamespace(status="missing", file_path=None)

        def fetch_resolved_kabutan_html_dir(self):
            return SimpleNamespace(status="missing", dir_path=None)

        def inspect_kabutan_html_package(self, *, zip_path):
            self.inspected_zip = zip_path
            return SimpleNamespace(zip_path=zip_path.resolve(), html_count=2, has_manifest=True)

        def save_kabutan_package_zip_cache(self, path):
            self.saved_zip = path

        def import_kabutan_html_package(self, **_kwargs):
            self.import_called = True
            raise AssertionError("upload should not extract zip")

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as archive:
        archive.writestr("manifest.json", "{}")
        archive.writestr("html/7203.html", "<html></html>")
    zip_buffer.seek(0)

    controller = FakeController()
    state = WebUiState(controller=controller)
    state.output_cache = {"7203|-": "cached"}
    client = create_app(state).test_client()

    html = client.post(
        "/kabutan-package/import",
        data={"kabutan_package_zip": (zip_buffer, "kabutan_html_package.zip")},
        content_type="multipart/form-data",
    ).data.decode("utf-8")

    zip_path = tmp_path / "web_uploaded_kabutan_html_package.zip"
    assert controller.inspected_zip == zip_path
    assert controller.saved_zip == zip_path
    assert state.kabutan_package_zip_path == zip_path
    assert state.kabutan_package_zip_signature is not None
    assert state.kabutan_html_dir is None
    assert not (tmp_path / "web_imported_kabutan_html_package").exists()
    assert controller.import_called is False
    assert state.output_cache == {}
    assert "株探HTMLパッケージZipをアップロードしました" in html
    assert "HTML: 2件" in html


def test_fetch_fundamental_extracts_uploaded_kabutan_package_once(tmp_path: Path):
    class FakeController:
        def __init__(self):
            self.file_cache = SimpleNamespace(base_dir=tmp_path)
            self.import_count = 0
            self.saved_dir = None
            self.analysis_dirs = []

        def fetch_output_cache_for_today(self):
            return {}

        def fetch_resolved_watchlist_path(self):
            return SimpleNamespace(status="missing", file_path=None)

        def fetch_resolved_kabutan_html_dir(self):
            return SimpleNamespace(status="missing", dir_path=None)

        def import_kabutan_html_package(self, *, zip_path, output_dir):
            self.import_count += 1
            html_dir = output_dir / "html"
            html_dir.mkdir(parents=True, exist_ok=True)
            return SimpleNamespace(html_dir=html_dir, manifest_path=None, html_count=1)

        def save_kabutan_html_dir_cache(self, path):
            self.saved_dir = path

        def fetch_analysis_output(self, **kwargs):
            self.analysis_dirs.append(kwargs["kabutan_html_dir"])
            return "Fundamental output"

        def save_output_cache_for_today(self, _output_cache):
            return None

        def fetch_institutional_summary_text(self, **_kwargs):
            return "機関投資サマリ\n時価総額：N/A"

    zip_path = tmp_path / "web_uploaded_kabutan_html_package.zip"
    zip_path.write_bytes(b"zip")

    controller = FakeController()
    state = WebUiState(controller=controller)
    state.watchlist = [("トヨタ", "7203")]
    state.selected_label = "トヨタ (7203)"
    state.kabutan_package_zip_path = zip_path
    state.kabutan_package_zip_signature = (zip_path.stat().st_size, zip_path.stat().st_mtime_ns)
    state.fundamental_summary_html = '<section class="summary-output">Summary</section>'
    client = create_app(state).test_client()

    html = client.post(
        "/fetch",
        data={"selected_stock": "トヨタ (7203)", "mode": "fundamental"},
    ).data.decode("utf-8")

    assert "summary-output" not in html
    assert "Fundamental output" in html
    assert state.fundamental_summary_html == ""
    assert controller.import_count == 1
    signature = (zip_path.stat().st_size, zip_path.stat().st_mtime_ns)
    assert state.kabutan_html_dir == tmp_path / "web_imported_kabutan_html_package" / f"{signature[0]}_{signature[1]}" / "html"
    assert controller.saved_dir == state.kabutan_html_dir
    assert controller.analysis_dirs == [state.kabutan_html_dir]

    client.post(
        "/fetch",
        data={"selected_stock": "トヨタ (7203)", "mode": "fundamental"},
    )

    assert controller.import_count == 1
    assert controller.analysis_dirs == [state.kabutan_html_dir, state.kabutan_html_dir]


def test_fundamental_summary_extracts_uploaded_kabutan_package(tmp_path: Path, monkeypatch):
    class FakeController:
        def __init__(self):
            self.file_cache = SimpleNamespace(base_dir=tmp_path)
            self.import_count = 0
            self.summary_dir = None

        def fetch_output_cache_for_today(self):
            return {}

        def fetch_resolved_watchlist_path(self):
            return SimpleNamespace(status="missing", file_path=None)

        def fetch_resolved_kabutan_html_dir(self):
            return SimpleNamespace(status="missing", dir_path=None)

        def import_kabutan_html_package(self, *, zip_path, output_dir):
            self.import_count += 1
            html_dir = output_dir / "html"
            html_dir.mkdir(parents=True, exist_ok=True)
            return SimpleNamespace(html_dir=html_dir, manifest_path=None, html_count=1)

        def save_kabutan_html_dir_cache(self, _path):
            return None

        def build_fundamental_summary_table(self, *, watchlist_entries, kabutan_html_dir):
            assert watchlist_entries == [("トヨタ", "7203")]
            self.summary_dir = kabutan_html_dir
            return "FUND_TABLE"

    monkeypatch.setattr("app.web.build_fundamental_summary_html", lambda table: f"<section>{table}</section>")

    zip_path = tmp_path / "web_uploaded_kabutan_html_package.zip"
    zip_path.write_bytes(b"zip")
    controller = FakeController()
    state = WebUiState(controller=controller)
    state.watchlist = [("トヨタ", "7203")]
    state.kabutan_package_zip_path = zip_path
    client = create_app(state).test_client()

    html = client.post(
        "/summary",
        data={"selected_stock": "トヨタ (7203)", "mode": "fundamental"},
    ).data.decode("utf-8")

    signature = (zip_path.stat().st_size, zip_path.stat().st_mtime_ns)
    expected_html_dir = tmp_path / "web_imported_kabutan_html_package" / f"{signature[0]}_{signature[1]}" / "html"
    assert "<section>FUND_TABLE</section>" in html
    assert controller.import_count == 1
    assert controller.summary_dir == expected_html_dir


def test_create_app_restores_cached_watchlist_kabutan_dir_and_package_zip(tmp_path: Path):
    class FakeController:
        def __init__(self):
            self.file_cache = SimpleNamespace(base_dir=tmp_path)
            self.watchlist_path = tmp_path / "watchlist.md"
            self.kabutan_dir = tmp_path / "kabutan"
            self.package_zip = tmp_path / "package.zip"
            self.watchlist_path.write_text("トヨタ (7203)\n", encoding="utf-8")
            self.kabutan_dir.mkdir()
            self.package_zip.write_bytes(b"zip")

        def fetch_output_cache_for_today(self):
            return {}

        def fetch_resolved_watchlist_path(self):
            return SimpleNamespace(status="ok", file_path=self.watchlist_path)

        def fetch_watchlist_entries(self, path):
            assert path == self.watchlist_path
            return [("トヨタ", "7203")]

        def fetch_resolved_kabutan_html_dir(self):
            return SimpleNamespace(status="ok", dir_path=self.kabutan_dir)

        def fetch_kabutan_package_zip_cache(self):
            return self.package_zip

    state = WebUiState(controller=FakeController())

    create_app(state)

    assert state.watchlist_path == tmp_path / "watchlist.md"
    assert state.watchlist == [("トヨタ", "7203")]
    assert state.selected_label == "トヨタ (7203)"
    assert state.kabutan_html_dir == tmp_path / "kabutan"
    assert state.kabutan_package_zip_path == tmp_path / "package.zip"
    assert state.kabutan_package_zip_signature == (
        state.kabutan_package_zip_path.stat().st_size,
        state.kabutan_package_zip_path.stat().st_mtime_ns,
    )
