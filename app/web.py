"""Flask Web UI that coexists with the Tkinter application."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:
    from flask import Flask, Response, render_template, request
except ModuleNotFoundError:  # pragma: no cover - allows helper tests without Flask installed
    Flask = Any  # type: ignore[misc, assignment]
    Response = Any  # type: ignore[misc, assignment]
    render_template = None  # type: ignore[assignment]
    request = None  # type: ignore[assignment]

from app.presentation.web_fundamental_output import WebTextBlock, build_fundamental_web_blocks
from app.presentation.web_fundamental_summary import build_fundamental_summary_html
from app.presentation.web_technical_summary import build_technical_summary_html
from app.data.file_cache import FileCache
from app.services.web_upload_workflow import WebUploadWorkflow
from app.ui_state_utils import build_output_cache_key
from app.web_state import DEFAULT_INSTITUTIONAL_SUMMARY, WebUiState, WebUiStateManager


def parse_uploaded_watchlist(data: bytes) -> list[tuple[str, str]]:
    return WebUploadWorkflow(file_cache=FileCache()).parse_uploaded_watchlist(data)


def build_copy_text(institutional_summary: str, output: str) -> str:
    """Build browser clipboard text. The fixed summary panel is always included."""

    summary = institutional_summary.strip()
    body = output.strip()
    if summary and body:
        return f"{summary}\n\n{body}"
    return summary or body


def resolve_existing_dir(raw_path: str) -> Path:
    return WebUploadWorkflow(file_cache=FileCache()).resolve_existing_dir(raw_path)


def create_app(state: WebUiState | None = None) -> Flask:
    if render_template is None or request is None:
        raise RuntimeError("Flask is not installed. Install dependencies with: pip install -r requirements.txt")

    app = Flask(__name__)
    ui_state = state or WebUiState()
    state_manager = WebUiStateManager(ui_state)
    upload_workflow = WebUploadWorkflow(file_cache=getattr(ui_state.controller, "file_cache", FileCache()))
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
                watchlist, path = upload_workflow.load_uploaded_watchlist(data)
            else:
                watchlist, path = upload_workflow.load_watchlist_from_path(request.form.get("watchlist_path", ""))
            ui_state.watchlist = watchlist
            ui_state.watchlist_path = path
            ui_state.controller.save_watchlist_path_cache(path)
            ui_state.fundamental_summary_html = ""
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
                path = upload_workflow.save_uploaded_kabutan_html_dir(uploaded_files)
            else:
                path = upload_workflow.resolve_existing_dir(request.form.get("kabutan_html_dir", ""))
            ui_state.kabutan_html_dir = path
            ui_state.kabutan_package_zip_path = None
            ui_state.kabutan_package_zip_signature = None
            ui_state.output_cache.clear()
            ui_state.controller.save_kabutan_html_dir_cache(path)
            clear_kabutan_package_zip_cache = getattr(ui_state.controller, "clear_kabutan_package_zip_cache", None)
            if callable(clear_kabutan_package_zip_cache):
                clear_kabutan_package_zip_cache()
            ui_state.fundamental_summary_html = ""
            ui_state.status = ui_state.view_model.build_kabutan_dir_selected_status()
        except Exception as exc:
            ui_state.status = str(exc)
        return _render(ui_state)

    @app.post("/kabutan-package/import")
    def import_kabutan_package() -> str:
        try:
            uploaded = request.files.get("kabutan_package_zip")
            zip_path = upload_workflow.save_uploaded_kabutan_html_package(uploaded)
            result = ui_state.controller.inspect_kabutan_html_package(zip_path=zip_path)
            ui_state.kabutan_package_zip_path = zip_path
            ui_state.kabutan_package_zip_signature = ui_state.controller.build_file_signature(zip_path)
            uploaded_html_dir = ui_state.controller.import_output_dir_for_signature(ui_state.kabutan_package_zip_signature) / "html"
            ui_state.kabutan_html_dir = uploaded_html_dir if ui_state.controller.html_dir_ready(uploaded_html_dir) else None
            ui_state.output_cache.clear()
            ui_state.controller.save_kabutan_package_zip_cache(zip_path)
            if ui_state.kabutan_html_dir is not None:
                ui_state.controller.save_kabutan_html_dir_cache(ui_state.kabutan_html_dir)
            ui_state.fundamental_summary_html = ""
            manifest_text = " / manifest: あり" if result.has_manifest else " / manifest: なし"
            extract_text = (
                f" / 展開済み: {ui_state.kabutan_html_dir}"
                if ui_state.kabutan_html_dir is not None
                else " / Fundamental取得時に展開します。"
            )
            ui_state.status = (
                "株探HTMLパッケージZipをアップロードしました。"
                f" HTML: {result.html_count}件"
                f"{manifest_text}"
                f"{extract_text}"
            )
        except Exception as exc:
            ui_state.status = f"株探HTMLパッケージアップロード失敗: {exc}"
        return _render(ui_state)

    @app.post("/fetch")
    def fetch_output() -> str:
        state_manager.sync_form_selection(
            request.form.get("selected_stock", ui_state.selected_label),
            request.form.get("mode", ui_state.mode),
        )
        ui_state.fundamental_summary_html = ""
        selected = state_manager.selected_stock()
        if selected is None:
            ui_state.status = ui_state.view_model.build_missing_stock_status()
            return _render(ui_state)
        if ui_state.mode != "technical":
            try:
                _ensure_kabutan_html_dir_for_fundamental(ui_state)
            except Exception as exc:
                ui_state.status = f"株探HTMLパッケージ展開失敗: {exc}"
                return _render(ui_state)
        if ui_state.mode != "technical" and ui_state.kabutan_html_dir is None:
            ui_state.status = ui_state.view_model.build_kabutan_dir_restore_required_status()
            return _render(ui_state)

        name, code4 = selected
        try:
            cache_key = (
                None
                if ui_state.mode == "technical"
                else build_output_cache_key(code4, ui_state.kabutan_html_dir)
            )
            result = ui_state.controller.fetch_output_for_mode(
                name=name,
                code4=code4,
                mode=ui_state.mode,
                output_cache=ui_state.output_cache,
                output_cache_key=cache_key,
                kabutan_html_dir=ui_state.kabutan_html_dir,
            )
            ui_state.output = result.output
            ui_state.institutional_summary = result.institutional_summary
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
            ui_state.fundamental_summary_html = ""
            return _render(ui_state)
        try:
            if ui_state.mode != "technical":
                _ensure_kabutan_html_dir_for_fundamental(ui_state)
                if ui_state.kabutan_html_dir is None:
                    ui_state.status = ui_state.view_model.build_kabutan_dir_restore_required_status()
                    ui_state.fundamental_summary_html = ""
                    return _render(ui_state)

            table = ui_state.controller.build_summary_table_for_mode(
                mode=ui_state.mode,
                watchlist_entries=ui_state.watchlist,
                kabutan_html_dir=ui_state.kabutan_html_dir,
            )
            if ui_state.mode == "technical":
                ui_state.fundamental_summary_html = build_technical_summary_html(table)
                ui_state.status = "Technicalサマリを表示しました。"
            else:
                ui_state.fundamental_summary_html = build_fundamental_summary_html(table)
                ui_state.status = "Fundamentalサマリを表示しました。"
        except Exception as exc:
            ui_state.status = f"{ui_state.view_model.build_summary_failed_status()} {exc}"
            ui_state.fundamental_summary_html = ""
        return _render(ui_state)

    @app.get("/download")
    def download_output() -> Response:
        selected = state_manager.selected_stock()
        filename = f"stock_fundamental_prompt_{selected[1]}.txt" if selected else "stock_fundamental_prompt.txt"
        content = build_copy_text(ui_state.institutional_summary, ui_state.output)
        response = app.response_class(content, mimetype="text/plain; charset=utf-8")
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"
        return response

    return app


def _ensure_kabutan_html_dir_for_fundamental(state: WebUiState) -> None:
    zip_path = state.kabutan_package_zip_path
    if zip_path is None:
        return
    result = state.controller.resolve_imported_kabutan_package(
        zip_path=zip_path,
        current_signature=state.kabutan_package_zip_signature,
        current_html_dir=state.kabutan_html_dir,
    )
    state.kabutan_html_dir = result.html_dir
    state.kabutan_package_zip_signature = result.signature
    if result.output_cache_should_clear:
        state.output_cache.clear()


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
        summary_html=state.fundamental_summary_html,
    )


def main() -> None:
    port = int(os.environ.get("PORT", "8080"))
    create_app().run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
