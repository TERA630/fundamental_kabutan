"""Flask Web UI that coexists with the Tkinter application."""

from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path
from typing import Any

try:
    from flask import Flask, Response, render_template, request
except ModuleNotFoundError:  # pragma: no cover - allows helper tests without Flask installed
    Flask = Any  # type: ignore[misc, assignment]
    Response = Any  # type: ignore[misc, assignment]
    render_template = None  # type: ignore[assignment]
    request = None  # type: ignore[assignment]

from app.gui_state_utils import build_output_cache_key
from app.presentation.web_fundamental_output import WebTextBlock, build_fundamental_web_blocks
from app.presentation.web_fundamental_summary import build_fundamental_summary_html
from app.presentation.web_technical_summary import build_technical_summary_html
from app.services.watchlist_service import WatchlistService
from app.web_state import DEFAULT_INSTITUTIONAL_SUMMARY, WebUiState, WebUiStateManager

UPLOAD_WATCHLIST_CACHE_NAME = "web_uploaded_watchlist.md"
UPLOAD_KABUTAN_HTML_DIR_NAME = "web_uploaded_kabutan_html"
UPLOAD_KABUTAN_PACKAGE_NAME = "web_uploaded_kabutan_html_package.zip"
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
    if render_template is None or request is None:
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
            uploaded_files = request.files.getlist("kabutan_html_files")
            if any(uploaded.filename for uploaded in uploaded_files):
                path = save_uploaded_kabutan_html_dir(ui_state, uploaded_files)
            else:
                path = resolve_existing_dir(request.form.get("kabutan_html_dir", ""))
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
            zip_path = save_uploaded_kabutan_html_package(ui_state, uploaded)
            result = ui_state.controller.inspect_kabutan_html_package(zip_path=zip_path)
            ui_state.kabutan_package_zip_path = zip_path
            ui_state.kabutan_package_zip_signature = _file_signature(zip_path)
            uploaded_html_dir = _import_output_dir_for_signature(ui_state, ui_state.kabutan_package_zip_signature) / "html"
            ui_state.kabutan_html_dir = uploaded_html_dir if _html_dir_ready(uploaded_html_dir) else None
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
        try:
            if ui_state.mode == "technical":
                technical_table = ui_state.controller.build_technical_summary_table(
                    watchlist_entries=ui_state.watchlist,
                )
                ui_state.fundamental_summary_html = build_technical_summary_html(technical_table)
                ui_state.status = "Technicalサマリを表示しました。"
            else:
                _ensure_kabutan_html_dir_for_fundamental(ui_state)
                if ui_state.kabutan_html_dir is None:
                    ui_state.status = ui_state.view_model.build_kabutan_dir_restore_required_status()
                    ui_state.fundamental_summary_html = ""
                    return _render(ui_state)
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


def _file_signature(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return (path.stat().st_size, digest.hexdigest()[:16])


def _import_output_dir_for_signature(state: WebUiState, signature: tuple[int, str]) -> Path:
    size, digest = signature
    return state.controller.file_cache.base_dir / WEB_KABUTAN_IMPORTED_PACKAGE_DIR_NAME / f"{size}_{digest}"


def _html_dir_ready(html_dir: Path) -> bool:
    return html_dir.exists() and html_dir.is_dir() and any(html_dir.glob("*.html"))


def _ensure_kabutan_html_dir_for_fundamental(state: WebUiState) -> None:
    zip_path = state.kabutan_package_zip_path
    if zip_path is None:
        return
    if not zip_path.exists() or not zip_path.is_file():
        raise ValueError("アップロード済みの株探HTMLパッケージZipが見つかりません。")

    signature = _file_signature(zip_path)
    if (
        state.kabutan_package_zip_signature == signature
        and state.kabutan_html_dir is not None
        and _html_dir_ready(state.kabutan_html_dir)
    ):
        return

    output_dir = _import_output_dir_for_signature(state, signature)
    html_dir = output_dir / "html"
    if _html_dir_ready(html_dir):
        state.kabutan_html_dir = html_dir
        state.kabutan_package_zip_signature = signature
        state.controller.save_kabutan_html_dir_cache(html_dir)
        return

    if (
        state.kabutan_html_dir == html_dir
        and state.kabutan_package_zip_signature == signature
        and _html_dir_ready(html_dir)
    ):
        return

    result = state.controller.import_kabutan_html_package(zip_path=zip_path, output_dir=output_dir)
    state.kabutan_html_dir = result.html_dir
    state.kabutan_package_zip_signature = signature
    state.output_cache.clear()
    state.controller.save_kabutan_html_dir_cache(result.html_dir)


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
