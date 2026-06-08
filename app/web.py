"""Flask Web UI that coexists with the Tkinter application."""

from __future__ import annotations

import os
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
from app.presentation.web_fundamental_output import WebTextBlock, build_fundamental_web_blocks
from app.presentation.web_fundamental_summary import build_fundamental_summary_html
from app.services.watchlist_service import WatchlistService
from app.web_state import DEFAULT_INSTITUTIONAL_SUMMARY, WebUiState, WebUiStateManager

UPLOAD_WATCHLIST_CACHE_NAME = "web_uploaded_watchlist.md"


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
                ui_state.fundamental_summary_html = ""
                ui_state.status = ui_state.view_model.build_loaded_status(len(ui_state.watchlist))
            else:
                raw_path = request.form.get("watchlist_path", "").strip()
                if not raw_path:
                    raise ValueError("監視銘柄ファイルをアップロードするか、パスを入力してください。")
                path = Path(raw_path).expanduser().resolve()
                ui_state.watchlist = watchlist_service.load_from_file(path)
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
            path = resolve_existing_dir(request.form.get("kabutan_html_dir", ""))
            ui_state.kabutan_html_dir = path
            ui_state.output_cache.clear()
            ui_state.controller.save_kabutan_html_dir_cache(path)
            ui_state.fundamental_summary_html = ""
            ui_state.status = ui_state.view_model.build_kabutan_dir_selected_status()
        except Exception as exc:
            ui_state.status = str(exc)
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
            ui_state.fundamental_summary_html = ""
            return _render(ui_state)
        if ui_state.kabutan_html_dir is None:
            ui_state.status = ui_state.view_model.build_kabutan_dir_restore_required_status()
            ui_state.fundamental_summary_html = ""
            return _render(ui_state)
        if ui_state.mode == "technical":
            ui_state.status = "Technicalモードではサマリ表示は無効です。"
            ui_state.fundamental_summary_html = ""
            return _render(ui_state)

        try:
            table = ui_state.controller.build_fundamental_summary_table(
                watchlist_entries=ui_state.watchlist,
                kabutan_html_dir=ui_state.kabutan_html_dir,
            )
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


def _save_uploaded_watchlist(state: WebUiState, data: bytes) -> Path:
    path = state.controller.file_cache.base_dir / UPLOAD_WATCHLIST_CACHE_NAME
    path.write_bytes(data)
    return path


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
