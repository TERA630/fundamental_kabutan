"""Flask Web UI that coexists with the Tkinter application."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
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

from app.data.watchlist_repository import fetch_watchlist_entries, parse_watchlist_text
from app.gui_controller import FundamentalGuiController
from app.gui_state import build_output_cache_key, build_stock_choices, get_selected_stock
from app.gui_view_model import GuiViewModel
from app.presentation.web_fundamental_output import build_fundamental_web_blocks

DEFAULT_INSTITUTIONAL_SUMMARY = "機関投資サマリ\n時価総額：N/A\n流動性：N/A\n機関投資スコア：N/A"
UPLOAD_WATCHLIST_CACHE_NAME = "web_uploaded_watchlist.md"


@dataclass
class WebUiState:
    """In-memory state for the single-process Flask UI."""

    controller: FundamentalGuiController = field(default_factory=FundamentalGuiController)
    view_model: GuiViewModel = field(default_factory=GuiViewModel)
    watchlist_path: Path | None = None
    kabutan_html_dir: Path | None = None
    watchlist: list[tuple[str, str]] = field(default_factory=list)
    output_cache: dict[str, str] = field(default_factory=dict)
    selected_label: str = ""
    mode: str = "fundamental"
    output: str = ""
    institutional_summary: str = DEFAULT_INSTITUTIONAL_SUMMARY
    status: str = field(default_factory=GuiViewModel.build_initial_status)

    @property
    def stock_choices(self) -> list[str]:
        choices, _mapping = build_stock_choices(self.watchlist)
        return choices


def decode_watchlist_upload(data: bytes) -> str:
    """Decode an uploaded watchlist using the same encodings accepted by file loading."""

    last_error: UnicodeDecodeError | None = None
    for encoding in ("utf-8", "utf-8-sig", "cp932"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
    raise ValueError(f"監視銘柄ファイルを読み込めませんでした: {last_error}")


def parse_uploaded_watchlist(data: bytes) -> list[tuple[str, str]]:
    text = decode_watchlist_upload(data)
    entries = parse_watchlist_text(text)
    if not entries:
        raise ValueError(
            "監視銘柄ファイルから銘柄を抽出できませんでした。対応形式例: '銘柄名 (1234)', '1234  銘柄名', '銘柄名,1234'"
        )
    return entries


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
    _restore_cached_state(ui_state)

    @app.get("/")
    def index() -> str:
        return _render(ui_state)

    @app.post("/watchlist")
    def load_watchlist() -> str:
        try:
            uploaded = request.files.get("watchlist_file")
            if uploaded is not None and uploaded.filename:
                data = uploaded.read()
                ui_state.watchlist = parse_uploaded_watchlist(data)
                ui_state.watchlist_path = _save_uploaded_watchlist(ui_state, data)
                ui_state.controller.save_watchlist_path_cache(ui_state.watchlist_path)
                ui_state.status = ui_state.view_model.build_loaded_status(len(ui_state.watchlist))
            else:
                raw_path = request.form.get("watchlist_path", "").strip()
                if not raw_path:
                    raise ValueError("監視銘柄ファイルをアップロードするか、パスを入力してください。")
                path = Path(raw_path).expanduser().resolve()
                ui_state.watchlist = fetch_watchlist_entries(path)
                ui_state.watchlist_path = path
                ui_state.controller.save_watchlist_path_cache(path)
                ui_state.status = ui_state.view_model.build_loaded_status(len(ui_state.watchlist))
            _select_first_if_needed(ui_state)
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
            ui_state.status = ui_state.view_model.build_kabutan_dir_selected_status()
        except Exception as exc:
            ui_state.status = str(exc)
        return _render(ui_state)

    @app.post("/fetch")
    def fetch_output() -> str:
        _sync_form_selection(ui_state)
        selected = _selected_stock(ui_state)
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
        _sync_form_selection(ui_state)
        if not ui_state.watchlist:
            ui_state.status = ui_state.view_model.build_missing_stock_status()
            return _render(ui_state)
        if ui_state.kabutan_html_dir is None:
            ui_state.status = ui_state.view_model.build_kabutan_dir_restore_required_status()
            return _render(ui_state)
        try:
            output_dir = ui_state.watchlist_path.parent if ui_state.watchlist_path is not None else Path.cwd()
            output_path = ui_state.controller.build_and_save_fundamental_summary(
                watchlist_entries=ui_state.watchlist,
                output_dir=output_dir,
                kabutan_html_dir=ui_state.kabutan_html_dir,
            )
            ui_state.status = ui_state.view_model.build_saved_status(str(output_path))
        except Exception as exc:
            ui_state.status = f"{ui_state.view_model.build_summary_failed_status()} {exc}"
        return _render(ui_state)

    @app.get("/download")
    def download_output() -> Response:
        selected = _selected_stock(ui_state)
        filename = f"stock_fundamental_prompt_{selected[1]}.txt" if selected else "stock_fundamental_prompt.txt"
        content = build_copy_text(ui_state.institutional_summary, ui_state.output)
        response = app.response_class(content, mimetype="text/plain; charset=utf-8")
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"
        return response

    return app


def _restore_cached_state(state: WebUiState) -> None:
    state.output_cache = state.controller.fetch_output_cache_for_today()
    resolved_watchlist = state.controller.fetch_resolved_watchlist_path()
    if resolved_watchlist.status == "ok" and resolved_watchlist.file_path is not None:
        try:
            state.watchlist_path = resolved_watchlist.file_path
            state.watchlist = state.controller.fetch_watchlist_entries(resolved_watchlist.file_path)
            state.status = state.view_model.build_watchlist_restored_status(len(state.watchlist))
            _select_first_if_needed(state)
        except Exception:
            state.watchlist_path = None
            state.watchlist = []

    resolved_kabutan = state.controller.fetch_resolved_kabutan_html_dir()
    if resolved_kabutan.status == "ok":
        state.kabutan_html_dir = resolved_kabutan.dir_path


def _save_uploaded_watchlist(state: WebUiState, data: bytes) -> Path:
    path = state.controller.file_cache.base_dir / UPLOAD_WATCHLIST_CACHE_NAME
    path.write_bytes(data)
    return path


def _select_first_if_needed(state: WebUiState) -> None:
    choices = state.stock_choices
    if choices and state.selected_label not in choices:
        state.selected_label = choices[0]


def _sync_form_selection(state: WebUiState) -> None:
    state.selected_label = request.form.get("selected_stock", state.selected_label)
    state.mode = request.form.get("mode", state.mode)


def _selected_stock(state: WebUiState) -> tuple[str, str] | None:
    _choices, mapping = build_stock_choices(state.watchlist)
    return get_selected_stock(mapping, state.selected_label)


def _render(state: WebUiState) -> str:
    show_rich_output = state.mode != "technical" and bool(state.output.strip())
    return render_template(
        "index.html",
        state=state,
        copy_text=build_copy_text(state.institutional_summary, state.output),
        output_blocks=build_fundamental_web_blocks(state.output) if show_rich_output else [],
        show_rich_output=show_rich_output,
    )


def main() -> None:
    port = int(os.environ.get("PORT", "8080"))
    create_app().run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
