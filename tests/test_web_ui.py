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
    assert 'form action="/kabutan-package"' in html
    assert "HTMLを正規化してZip作成" in html
    assert 'form action="/kabutan-package/import"' in html
    assert 'name="kabutan_package_zip"' in html


def test_set_kabutan_dir_accepts_uploaded_html_folder(tmp_path: Path):
    class FakeController:
        def __init__(self):
            self.file_cache = SimpleNamespace(base_dir=tmp_path)
            self.saved_dir = None

        def fetch_output_cache_for_today(self):
            return {}

        def fetch_resolved_watchlist_path(self):
            return SimpleNamespace(status="missing", file_path=None)

        def fetch_resolved_kabutan_html_dir(self):
            return SimpleNamespace(status="missing", dir_path=None)

        def save_kabutan_html_dir_cache(self, path):
            self.saved_dir = path

    controller = FakeController()
    state = WebUiState(controller=controller)
    client = create_app(state).test_client()

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
    assert controller.saved_dir == state.kabutan_html_dir
    assert (state.kabutan_html_dir / "7203.html").read_bytes() == b"<html>7203</html>"
    assert (state.kabutan_html_dir / "7974.htm").read_bytes() == b"<html>7974</html>"
    assert not (state.kabutan_html_dir / "readme.txt").exists()
    assert "株探HTMLフォルダを設定しました" in html


def test_build_kabutan_package_sets_normalized_html_dir_and_shows_download(tmp_path: Path):
    class FakeController:
        def __init__(self):
            self.file_cache = SimpleNamespace(base_dir=tmp_path)
            self.saved_dir = None
            self.package_source = None

        def fetch_output_cache_for_today(self):
            return {"7203|-": "cached"}

        def fetch_resolved_watchlist_path(self):
            return SimpleNamespace(status="missing", file_path=None)

        def fetch_resolved_kabutan_html_dir(self):
            return SimpleNamespace(status="missing", dir_path=None)

        def save_kabutan_html_dir_cache(self, path):
            self.saved_dir = path

        def build_kabutan_html_package(self, *, source_dir, output_dir):
            self.package_source = source_dir
            html_dir = output_dir / "html"
            html_dir.mkdir(parents=True)
            manifest_path = output_dir / "manifest.json"
            zip_path = output_dir / "kabutan_html_package.zip"
            manifest_path.write_text("{}", encoding="utf-8")
            zip_path.write_bytes(b"zip")
            return SimpleNamespace(
                html_dir=html_dir,
                manifest_path=manifest_path,
                zip_path=zip_path,
                normalized_count=1,
                skipped_count=0,
            )

    source_dir = tmp_path / "source"
    source_dir.mkdir()
    controller = FakeController()
    state = WebUiState(controller=controller)
    state.kabutan_html_dir = source_dir
    state.output_cache = {"7203|-": "cached"}
    client = create_app(state).test_client()

    html = client.post("/kabutan-package").data.decode("utf-8")

    assert controller.package_source == source_dir
    assert state.kabutan_html_dir == (tmp_path / "web_kabutan_html_package" / "html")
    assert controller.saved_dir == state.kabutan_html_dir
    assert state.output_cache == {}
    assert "正規化: 1件 / スキップ: 0件" in html
    assert 'href="/kabutan-package/download"' in html


def test_import_kabutan_package_zip_sets_html_dir(tmp_path: Path):
    class FakeController:
        def __init__(self):
            self.file_cache = SimpleNamespace(base_dir=tmp_path)
            self.saved_dir = None
            self.imported_zip = None

        def fetch_output_cache_for_today(self):
            return {"7203|-": "cached"}

        def fetch_resolved_watchlist_path(self):
            return SimpleNamespace(status="missing", file_path=None)

        def fetch_resolved_kabutan_html_dir(self):
            return SimpleNamespace(status="missing", dir_path=None)

        def save_kabutan_html_dir_cache(self, path):
            self.saved_dir = path

        def import_kabutan_html_package(self, *, zip_path, output_dir):
            self.imported_zip = zip_path
            html_dir = output_dir / "html"
            html_dir.mkdir(parents=True)
            manifest_path = output_dir / "manifest.json"
            manifest_path.write_text("{}", encoding="utf-8")
            return SimpleNamespace(
                html_dir=html_dir,
                manifest_path=manifest_path,
                html_count=2,
            )

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

    assert controller.imported_zip == tmp_path / "web_uploaded_kabutan_html_package.zip"
    assert state.kabutan_html_dir == tmp_path / "web_imported_kabutan_html_package" / "html"
    assert controller.saved_dir == state.kabutan_html_dir
    assert state.output_cache == {}
    assert "HTML: 2件" in html


def test_fetch_fundamental_clears_summary_html(tmp_path: Path):
    class FakeController:
        def fetch_output_cache_for_today(self):
            return {}

        def fetch_resolved_watchlist_path(self):
            return SimpleNamespace(status="missing", file_path=None)

        def fetch_resolved_kabutan_html_dir(self):
            return SimpleNamespace(status="missing", dir_path=None)

        def fetch_analysis_output(self, **_kwargs):
            return "Fundamental output"

        def save_output_cache_for_today(self, _output_cache):
            return None

        def fetch_institutional_summary_text(self, **_kwargs):
            return "機関投資サマリ\n時価総額：N/A"

    state = WebUiState(controller=FakeController())
    state.watchlist = [("トヨタ", "7203")]
    state.selected_label = "トヨタ (7203)"
    state.kabutan_html_dir = tmp_path
    state.fundamental_summary_html = '<section class="summary-output">Summary</section>'
    client = create_app(state).test_client()

    html = client.post(
        "/fetch",
        data={"selected_stock": "トヨタ (7203)", "mode": "fundamental"},
    ).data.decode("utf-8")

    assert "summary-output" not in html
    assert "Fundamental output" in html
    assert state.fundamental_summary_html == ""
