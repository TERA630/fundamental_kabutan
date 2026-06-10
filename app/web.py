"""Flask Web UI that coexists with the Tkinter application."""

from __future__ import annotations

import os
import shutil
from datetime import date
from pathlib import Path
from typing import Any

try:
    from flask import Flask, Response, render_template, request, send_file
except ModuleNotFoundError:  # pragma: no cover - allows helper tests without Flask installed
    Flask = Any  # type: ignore[misc, assignment]
    Response = Any  # type: ignore[misc, assignment]
    render_template = None  # type: ignore[assignment]
    request = None  # type: ignore[assignment]
    send_file = None  # type: ignore[assignment]

from app.gui_state_utils import build_output_cache_key
from app.gui_controller import build_fundamental_summary_filename, build_technical_summary_filename
from app.domain.builders.fundamental_summary import build_fundamental_summary_markdown
from app.domain.builders.technical_summary import build_technical_summary_markdown
from app.presentation.web_fundamental_output import WebTextBlock, build_fundamental_web_blocks
from app.presentation.web_fundamental_summary import build_fundamental_summary_html
from app.presentation.web_technical_summary import build_technical_summary_html
from app.services.watchlist_service import WatchlistService
from app.web_state import DEFAULT_INSTITUTIONAL_SUMMARY, WebUiState, WebUiStateManager

UPLOAD_WATCHLIST_CACHE_NAME = "web_uploaded_watchlist.md"
UPLOAD_KABUTAN_HTML_DIR_NAME = "web_uploaded_kabutan_html"
UPLOAD_KABUTAN_PACKAGE_NAME = "web_uploaded_kabutan_html_package.zip"
WEB_KABUTAN_PACKAGE_DIR_NAME = "web_kabutan_html_package"
WEB_KABUTAN_IMPORTED_PACKAGE_DIR_NAME = "web_imported_kabutan_html_package"
KABUTAN_HTML_SUFFIXES = {".html", ".htm"}


def parse_uploaded_watchlist(data: bytes) -> list[tuple[str, str]]:
    return WatchlistService().parse_uploaded(data)


def build_copy_text(institutional_summary: str, output: str) -> str:
    """Build browser clipboard text. The fixed summary panel is always included."""

    summary = institutional_summary.strip()
    body = output.strip()
    if summary and body:
        return f"{summary}\n\n{body}"
    return summary or body


def resolve_existing_dir(raw_path: str) -> Path:
    path = Path(raw_path.strip()).expanduser()
    if not raw_path.strip():
        raise ValueError("株探HTMLフォルダのコンテナ内パスを入力してください。")
    if not path.exists() or not path.is_dir():
        raise ValueError("株探HTMLフォルダが見つかりません。コンテナ内の既存ディレクトリを指定してください。")
    return path.resolve()


def save_uploaded_kabutan_html_dir(state: WebUiState, uploaded_files: list[Any]) -> Path:
    files = [
        uploaded
        for uploaded in uploaded_files
        if uploaded is not None
        and uploaded.filename
        and Path(uploaded.filename).suffix.lower() in KABUTAN_HTML_SUFFIXES
    ]
    if not files:
        raise ValueError("株探HTMLフォルダにHTMLファイルが見つかりませんでした。")

    upload_dir = state.controller.file_cache.base_dir / UPLOAD_KABUTAN_HTML_DIR_NAME
    if upload_dir.exists():
        shutil.rmtree(upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    used_names: set[str] = set()
    for uploaded in files:
        source_name = Path(uploaded.filename).name
        target_name = _dedupe_filename(source_name, used_names)
        uploaded.save(upload_dir / target_name)
    return upload_dir.resolve()


def save_uploaded_kabutan_html_package(state: WebUiState, uploaded_file: Any) -> Path:
    if uploaded_file is None or not uploaded_file.filename:
        raise ValueError("株探HTMLパッケージZipを選択してください。")
    if Path(uploaded_file.filename).suffix.lower() != ".zip":
        raise ValueError("株探HTMLパッケージはZipファイルを選択してください。")
    zip_path = state.controller.file_cache.base_dir / UPLOAD_KABUTAN_PACKAGE_NAME
    uploaded_file.save(zip_path)
    return zip_path


def _dedupe_filename(filename: str, used_names: set[str]) -> str:
    path = Path(filename)
    candidate = path.name
    index = 2
    while candidate.lower() in used_names:
        candidate = f"{path.stem}_{index}{path.suffix}"
        index += 1
    used_names.add(candidate.lower())
    return candidate


def create_app(state: WebUiState | None = None) -> Flask:
    if render_template is None or request is None or send_file is None:
        raise RuntimeError("Flask is not installed. Install dependencies with: pip install -r requirements.txt")

    app = Flask(__name__)
    ui_state = state or WebUiState()
    state_manager = WebUiStateManager(ui_state)
    watchlist_service = WatchlistService()
    state_manager.restore_cached_state()

    @app.get("/")
    def index() -> str:
        return _render(ui_state)

    @app.post("/watchlist")
    def load_watchlist() -> str:
        try:
            uploaded = request.files.get("watchlist_file")
            if uploaded is not None and uploaded.filename:
                data = uploaded.read()
                ui_state.watchlist = watchlist_service.parse_uploaded(data)
                ui_state.watchlist_path = _save_uploaded_watchlist(ui_state, data)
                ui_state.controller.save_watchlist_path_cache(ui_state.watchlist_path)
                _clear_summary(ui_state)
                ui_state.status = ui_state.view_model.build_loaded_status(len(ui_state.watchlist))
            else:
                raw_path = request.form.get("watchlist_path", "").strip()
                if not raw_path:
                    raise ValueError("監視銘柄ファイルをアップロードするか、パスを入力してください。")
                path = Path(raw_path).expanduser().resolve()
                ui_state.watchlist = watchlist_service.load_from_file(path)
                ui_state.watchlist_path = path
                ui_state.controller.save_watchlist_path_cache(path)
                _clear_summary(ui_state)
                ui_state.status = ui_state.view_model.build_loaded_status(len(ui_state.watchlist))
            state_manager.select_first_if_needed()
        except Exception as exc:
            ui_state.status = str(exc)
        return _render(ui_state)

    @app.post("/kabutan-dir")
    def set_kabutan_dir() -> str:
        try:
            uploaded_files = request.files.getlist("kabutan_html_files")
            if any(uploaded.filename for uploaded in uploaded_files):
                path = save_uploaded_kabutan_html_dir(ui_state, uploaded_files)
            else:
                path = resolve_existing_dir(request.form.get("kabutan_html_dir", ""))
            ui_state.kabutan_html_dir = path
            ui_state.output_cache.clear()
            ui_state.controller.save_kabutan_html_dir_cache(path)
            _clear_summary(ui_state)
            ui_state.status = ui_state.view_model.build_kabutan_dir_selected_status()
        except Exception as exc:
            ui_state.status = str(exc)
        return _render(ui_state)

    @app.post("/kabutan-package")
    def build_kabutan_package() -> str:
        try:
            if ui_state.kabutan_html_dir is None:
                ui_state.status = ui_state.view_model.build_kabutan_dir_restore_required_status()
                return _render(ui_state)

            result = ui_state.controller.build_kabutan_html_package(
                source_dir=ui_state.kabutan_html_dir,
                output_dir=ui_state.controller.file_cache.base_dir / WEB_KABUTAN_PACKAGE_DIR_NAME,
            )
            ui_state.kabutan_html_dir = result.html_dir
            ui_state.output_cache.clear()
            ui_state.controller.save_kabutan_html_dir_cache(result.html_dir)
            _clear_summary(ui_state)
            ui_state.status = (
                "株探HTMLを正規化してZipを作成しました。"
                f" 正規化: {result.normalized_count}件 / スキップ: {result.skipped_count}件"
                f" / manifest: {result.manifest_path}"
                f" / zip: {result.zip_path}"
            )
        except Exception as exc:
            ui_state.status = f"株探HTMLパッケージ作成失敗: {exc}"
        return _render(ui_state)

    @app.post("/kabutan-package/import")
    def import_kabutan_package() -> str:
        try:
            uploaded = request.files.get("kabutan_package_zip")
            zip_path = save_uploaded_kabutan_html_package(ui_state, uploaded)
            result = ui_state.controller.import_kabutan_html_package(
                zip_path=zip_path,
                output_dir=ui_state.controller.file_cache.base_dir / WEB_KABUTAN_IMPORTED_PACKAGE_DIR_NAME,
            )
            ui_state.kabutan_html_dir = result.html_dir
            ui_state.output_cache.clear()
            ui_state.controller.save_kabutan_html_dir_cache(result.html_dir)
            _clear_summary(ui_state)
            manifest_text = f" / manifest: {result.manifest_path}" if result.manifest_path is not None else ""
            ui_state.status = (
                "株探HTMLパッケージZipを展開しました。"
                f" HTML: {result.html_count}件"
                f" / html_dir: {result.html_dir}"
                f"{manifest_text}"
            )
        except Exception as exc:
            ui_state.status = f"株探HTMLパッケージ展開失敗: {exc}"
        return _render(ui_state)

    @app.get("/kabutan-package/download")
    def download_kabutan_package() -> Response:
        zip_path = ui_state.controller.file_cache.base_dir / WEB_KABUTAN_PACKAGE_DIR_NAME / "kabutan_html_package.zip"
        if not zip_path.exists():
            return app.response_class("株探HTMLパッケージが見つかりません。", status=404)
        return send_file(zip_path, as_attachment=True, download_name="kabutan_html_package.zip")

    @app.post("/fetch")
    def fetch_output() -> str:
        state_manager.sync_form_selection(
            request.form.get("selected_stock", ui_state.selected_label),
            request.form.get("mode", ui_state.mode),
        )
        _clear_summary(ui_state)
        selected = state_manager.selected_stock()
        if selected is None:
            ui_state.status = ui_state.view_model.build_missing_stock_status()
            return _render(ui_state)
        if ui_state.kabutan_html_dir is None:
            ui_state.status = ui_state.view_model.build_kabutan_dir_restore_required_status()
            return _render(ui_state)

        name, code4 = selected
        try:
            if ui_state.mode == "technical":
                ui_state.output = ui_state.controller.fetch_technical_output(name=name, code4=code4)
            else:
                cache_key = build_output_cache_key(code4, ui_state.kabutan_html_dir)
                ui_state.output = ui_state.controller.fetch_analysis_output(
                    name=name,
                    code4=code4,
                    output_cache=ui_state.output_cache,
                    output_cache_key=cache_key,
                    kabutan_html_dir=ui_state.kabutan_html_dir,
                )
                ui_state.controller.save_output_cache_for_today(ui_state.output_cache)
            ui_state.institutional_summary = ui_state.controller.fetch_institutional_summary_text(
                name=name,
                code4=code4,
                kabutan_html_dir=ui_state.kabutan_html_dir,
            )
            ui_state.status = ui_state.view_model.build_generated_status(name, code4)
        except Exception as exc:
            ui_state.status = f"{ui_state.view_model.build_fetch_failed_status()} {exc}"
        return _render(ui_state)

    @app.post("/summary")
    def build_summary() -> str:
        state_manager.sync_form_selection(
            request.form.get("selected_stock", ui_state.selected_label),
            request.form.get("mode", ui_state.mode),
        )
        if not ui_state.watchlist:
            ui_state.status = ui_state.view_model.build_missing_stock_status()
            _clear_summary(ui_state)
            return _render(ui_state)
        if ui_state.mode != "technical" and ui_state.kabutan_html_dir is None:
            ui_state.status = ui_state.view_model.build_kabutan_dir_restore_required_status()
            _clear_summary(ui_state)
            return _render(ui_state)

        try:
            today = date.today()
            if ui_state.mode == "technical":
                technical_table = ui_state.controller.build_technical_summary_table(
                    watchlist_entries=ui_state.watchlist,
                )
                html = build_technical_summary_html(technical_table)
                markdown = build_technical_summary_markdown(technical_table)
                _store_summary(
                    ui_state,
                    kind="technical",
                    html=html,
                    markdown=markdown,
                    filename=build_technical_summary_filename(today=today),
                )
                ui_state.status = "Technicalサマリを表示しました。"
            else:
                table = ui_state.controller.build_fundamental_summary_table(
                    watchlist_entries=ui_state.watchlist,
                    kabutan_html_dir=ui_state.kabutan_html_dir,
                )
                html = build_fundamental_summary_html(table)
                markdown = build_fundamental_summary_markdown(table)
                _store_summary(
                    ui_state,
                    kind="fundamental",
                    html=html,
                    markdown=markdown,
                    filename=build_fundamental_summary_filename(today=today),
                )
                ui_state.status = "Fundamentalサマリを表示しました。"
        except Exception as exc:
            ui_state.status = f"{ui_state.view_model.build_summary_failed_status()} {exc}"
            _clear_summary(ui_state)
        return _render(ui_state)

    @app.get("/summary/download.md")
    def download_summary_markdown() -> Response:
        if not ui_state.summary_markdown:
            return app.response_class("サマリがまだ生成されていません。", status=404)
        response = app.response_class(ui_state.summary_markdown, mimetype="text/markdown; charset=utf-8")
        filename = ui_state.summary_filename or "summary.md"
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"
        return response

    @app.get("/summary/download.html")
    def download_summary_html() -> Response:
        if not ui_state.summary_html:
            return app.response_class("サマリがまだ生成されていません。", status=404)
        filename = _summary_html_filename(ui_state.summary_filename)
        response = app.response_class(ui_state.summary_html, mimetype="text/html; charset=utf-8")
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"
        return response

    @app.get("/download")
    def download_output() -> Response:
        selected = state_manager.selected_stock()
        filename = f"stock_fundamental_prompt_{selected[1]}.txt" if selected else "stock_fundamental_prompt.txt"
        content = build_copy_text(ui_state.institutional_summary, ui_state.output)
        response = app.response_class(content, mimetype="text/plain; charset=utf-8")
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"
        return response

    return app


def _save_uploaded_watchlist(state: WebUiState, data: bytes) -> Path:
    path = state.controller.file_cache.base_dir / UPLOAD_WATCHLIST_CACHE_NAME
    path.write_bytes(data)
    return path


def _clear_summary(state: WebUiState) -> None:
    state.fundamental_summary_html = ""
    state.summary_kind = ""
    state.summary_markdown = ""
    state.summary_html = ""
    state.summary_filename = ""


def _store_summary(
    state: WebUiState,
    *,
    kind: str,
    html: str,
    markdown: str,
    filename: str,
) -> None:
    state.fundamental_summary_html = html
    state.summary_kind = kind
    state.summary_html = html
    state.summary_markdown = markdown
    state.summary_filename = filename


def _summary_html_filename(markdown_filename: str) -> str:
    if markdown_filename.endswith(".md"):
        return f"{markdown_filename[:-3]}.html"
    return "summary.html"


def _kabutan_package_zip_exists(state: WebUiState) -> bool:
    file_cache = getattr(state.controller, "file_cache", None)
    base_dir = getattr(file_cache, "base_dir", None)
    if base_dir is None:
        return False
    return (base_dir / WEB_KABUTAN_PACKAGE_DIR_NAME / "kabutan_html_package.zip").exists()


def _render(state: WebUiState) -> str:
    output_blocks = (
        [WebTextBlock(kind="text", text=state.output)]
        if state.mode == "technical"
        else build_fundamental_web_blocks(state.output)
    )
    return render_template(
        "index.html",
        state=state,
        copy_text=build_copy_text(state.institutional_summary, state.output),
        output_blocks=output_blocks,
        kabutan_package_zip_exists=_kabutan_package_zip_exists(state),
        summary_html=state.fundamental_summary_html,
    )


def main() -> None:
    port = int(os.environ.get("PORT", "8080"))
    create_app().run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
