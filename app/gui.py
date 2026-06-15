"""GUI layer: Tkinter application wiring and event handling."""

from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from app.gui_state import (
    GuiState,
    build_default_output_filename,
    build_output_cache_key,
)
from app.gui_state_manager import GuiStateManager
from app.gui_view import FundamentalView
from app.gui_view_model import GuiViewModel
from app.services.analysis_application_service import AnalysisApplicationService


class FundamentalApp:
    """GUI層: 画面イベント連携と状態遷移を担当。"""

    def __init__(self, master: tk.Tk):
        self.master = master
        self.master.title("ファンダメンタル評価 v8（株探/yFinanceベース）")
        self.master.geometry("1040x820")

        self.state = GuiState()
        self.controller = AnalysisApplicationService()
        self.view_model = GuiViewModel()
        self.state_manager = GuiStateManager(
            state=self.state,
            controller=self.controller,
            view_model=self.view_model,
        )

        self.path_var = tk.StringVar(value="監視銘柄ファイル未選択")
        self.kabutan_dir_var = tk.StringVar(value="株探HTMLフォルダ未選択")
        self.stock_var = tk.StringVar()
        self.status_var = tk.StringVar(value=GuiViewModel.build_initial_status())
        self.institutional_summary_var = tk.StringVar(value="機関投資サマリ\n時価総額：N/A\n流動性：N/A\n機関投資スコア：N/A")

        self.view = FundamentalView(
            self.master,
            self.path_var,
            self.stock_var,
            self.status_var,
            self.kabutan_dir_var,
            self.institutional_summary_var,
        )
        self.view.build_ui(
            on_open=self.open_watchlist,
            on_select=self.on_stock_selected,
            on_fetch=self.generate_text,
            on_copy=self.copy_text,
            on_save=self.save_text,
            on_open_kabutan_dir=self.open_kabutan_html_dir,
            on_build_kabutan_package=self.build_kabutan_html_package,
            on_summary=self.generate_summary,
            on_tab_changed=self.on_tab_changed,
        )
        self.state_manager.restore_output_cache()
        self._restore_watchlist()
        self._restore_kabutan_html_dir()

    def set_busy(self, busy: bool, status: str | None = None):
        self.state.is_fetching = busy
        self.view.set_busy(busy, status)

    def open_watchlist(self):
        path = filedialog.askopenfilename(
            title="監視銘柄ファイルを選択",
            filetypes=[("Markdown/Text", "*.md *.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            choices = self.state_manager.load_watchlist(Path(path))
        except Exception as exc:
            messagebox.showerror("読込失敗", str(exc))
            return

        self.path_var.set(str(self.state.watchlist_path))
        self._apply_stock_choices(choices)

    def _restore_watchlist(self) -> None:
        try:
            restored = self.state_manager.restore_watchlist()
        except Exception:
            return
        if restored is None:
            return
        path, choices, status = restored
        self.path_var.set(str(path))
        self._apply_stock_choices(choices)
        self.status_var.set(status)

    def open_kabutan_html_dir(self):
        path = filedialog.askdirectory(title="株探HTML保存フォルダを選択")
        if not path:
            return
        status = self.state_manager.select_kabutan_html_dir(Path(path))
        self.kabutan_dir_var.set(str(self.state.kabutan_html_dir))
        self.status_var.set(status)

    def _restore_kabutan_html_dir(self) -> None:
        restored = self.state_manager.restore_kabutan_html_dir()
        if restored is None:
            return
        path, status = restored
        self.kabutan_dir_var.set(str(path))
        self.status_var.set(status)

    def _apply_stock_choices(self, choices: list[str]) -> None:
        self.view.set_stock_choices(choices)

        if choices:
            self.stock_var.set(choices[0])
            self.status_var.set(self.view_model.build_loaded_status(len(choices)))
        else:
            self.stock_var.set("")
            self.view.clear_all_text()
            self.status_var.set(self.view_model.build_no_stock_found_status())

    def on_stock_selected(self, _event=None):
        self.status_var.set(self.view_model.build_selected_status())

    def on_tab_changed(self, _event=None):
        self.status_var.set(self.view_model.build_selected_status())

    def selected_stock(self) -> tuple[str, str] | None:
        return self.state_manager.selected_stock(self.stock_var.get())

    def _require_selected_stock(self) -> tuple[str, str] | None:
        selected = self.selected_stock()
        if selected is None:
            self.status_var.set(self.view_model.build_missing_stock_status())
            return None
        return selected

    def _render_output(self, output: str, status: str, mode: str | None = None):
        self.view.render_output(output, mode=mode)
        self.set_busy(False, status)

    def _render_output_with_summary(self, output: str, summary: str, status: str, mode: str):
        self.institutional_summary_var.set(summary)
        self._render_output(output, status, mode=mode)

    def _handle_fetch_error(self, message: str):
        self.set_busy(False, self.view_model.build_fetch_failed_status())
        messagebox.showerror("取得失敗", message)

    def _handle_summary_error(self, message: str):
        self.set_busy(False, self.view_model.build_summary_failed_status())
        messagebox.showerror("サマリ作成失敗", message)

    def _fetch_worker(self, name: str, code4: str, cache_key: str):
        try:
            output = self.controller.fetch_analysis_output(
                name=name,
                code4=code4,
                output_cache=self.state.output_cache,
                output_cache_key=cache_key,
                kabutan_html_dir=self.state.kabutan_html_dir,
            )
            summary = self.controller.fetch_institutional_summary_text(
                name=name,
                code4=code4,
                kabutan_html_dir=self.state.kabutan_html_dir,
            )
            self.controller.save_output_cache_for_today(self.state.output_cache)
            self.master.after(0, lambda: self._render_output_with_summary(output, summary, self.view_model.build_generated_status(name, code4), "fundamental"))
        except Exception as exc:
            self.master.after(0, lambda msg=str(exc): self._handle_fetch_error(msg))

    def _technical_fetch_worker(self, name: str, code4: str):
        try:
            output = self.controller.fetch_technical_output(name=name, code4=code4)
            summary = self.controller.fetch_institutional_summary_text(
                name=name,
                code4=code4,
                kabutan_html_dir=self.state.kabutan_html_dir,
            )
            self.master.after(0, lambda: self._render_output_with_summary(output, summary, self.view_model.build_generated_status(name, code4), "technical"))
        except Exception as exc:
            self.master.after(0, lambda msg=str(exc): self._handle_fetch_error(msg))

    def _summary_worker(self, output_dir: Path, mode: str):
        try:
            if mode == "technical":
                output_path = self.controller.build_and_save_technical_summary(
                    watchlist_entries=self.state.watchlist,
                    output_dir=output_dir,
                )
            else:
                output_path = self.controller.build_and_save_fundamental_summary(
                    watchlist_entries=self.state.watchlist,
                    output_dir=output_dir,
                    kabutan_html_dir=self.state.kabutan_html_dir,
                )
            self.master.after(0, lambda path=output_path: self.set_busy(False, self.view_model.build_saved_status(str(path))))
        except Exception as exc:
            self.master.after(0, lambda msg=str(exc): self._handle_summary_error(msg))

    def _kabutan_package_worker(self, source_dir: Path, output_dir: Path):
        try:
            result = self.controller.build_kabutan_html_package(source_dir=source_dir, output_dir=output_dir)
            self.state.kabutan_html_dir = result.html_dir
            self.controller.save_kabutan_html_dir_cache(result.html_dir)
            self.state_manager.clear_output_cache()

            def done():
                self.kabutan_dir_var.set(str(result.html_dir))
                self.set_busy(
                    False,
                    (
                        "株探HTMLを正規化してZipを作成しました。"
                        f" 正規化: {result.normalized_count}件 / スキップ: {result.skipped_count}件"
                        f" / zip: {result.zip_path}"
                    ),
                )

            self.master.after(0, done)
        except Exception as exc:
            self.master.after(0, lambda msg=str(exc): self._handle_summary_error(msg))

    def _require_kabutan_html_dir(self) -> bool:
        if self.state.kabutan_html_dir is None:
            self.status_var.set(self.view_model.build_kabutan_dir_restore_required_status())
            self.open_kabutan_html_dir()
            if self.state.kabutan_html_dir is None:
                return False
        return True

    def _render_cached_output(self, name: str, code4: str, cache_key: str) -> bool:
        cached_output = self.state.output_cache.get(cache_key)
        if cached_output is None:
            return False
        self._render_output(cached_output, self.view_model.build_cached_status(name, code4))
        return True

    def _rotate_output_cache_if_needed(self) -> None:
        self.state_manager.rotate_output_cache_if_needed()

    def _start_fetch_thread(self, name: str, code4: str, cache_key: str) -> None:
        self.set_busy(True, self.view_model.build_fetching_status(name, code4))
        thread = threading.Thread(target=self._fetch_worker, args=(name, code4, cache_key), daemon=True)
        thread.start()

    def _start_technical_fetch_thread(self, name: str, code4: str) -> None:
        self.set_busy(True, self.view_model.build_fetching_status(name, code4))
        thread = threading.Thread(target=self._technical_fetch_worker, args=(name, code4), daemon=True)
        thread.start()

    def generate_text(self):
        if self.state.is_fetching:
            return

        self._rotate_output_cache_if_needed()

        selected = self._require_selected_stock()
        if selected is None:
            return

        name, code4 = selected
        if self.view.current_mode() == "technical":
            self._start_technical_fetch_thread(name, code4)
            return

        if not self._require_kabutan_html_dir():
            return

        cache_key = build_output_cache_key(code4, self.state.kabutan_html_dir)
        if self._render_cached_output(name, code4, cache_key):
            return

        self._start_fetch_thread(name, code4, cache_key)

    def generate_summary(self):
        if self.state.is_fetching:
            return

        if not self.state.watchlist:
            self.status_var.set(self.view_model.build_missing_stock_status())
            return

        mode = self.view.current_mode()
        if mode != "technical" and not self._require_kabutan_html_dir():
            return

        output_dir = self.state.watchlist_path.parent if self.state.watchlist_path is not None else Path.cwd()
        self.set_busy(True, self.view_model.build_summary_running_status())
        thread = threading.Thread(target=self._summary_worker, args=(output_dir, mode), daemon=True)
        thread.start()

    def build_kabutan_html_package(self):
        if self.state.is_fetching:
            return
        if self.view.current_mode() == "technical":
            return
        if not self._require_kabutan_html_dir():
            return

        source_dir = self.state.kabutan_html_dir
        if source_dir is None:
            return
        output_dir = source_dir.parent / "kabutan_html_package"
        self.set_busy(True, "株探HTMLを正規化してZipを作成中...")
        thread = threading.Thread(target=self._kabutan_package_worker, args=(source_dir, output_dir), daemon=True)
        thread.start()

    def copy_text(self):
        content = self.view.get_text_content()
        if not content:
            self.status_var.set(self.view_model.build_missing_copy_content_status())
            return
        self.master.clipboard_clear()
        self.master.clipboard_append(content)
        self.status_var.set(self.view_model.build_copied_status())

    def save_text(self):
        content = self.view.get_text_content()
        if not content:
            self.status_var.set(self.view_model.build_missing_save_content_status())
            return
        selected = self.selected_stock()
        default_name = build_default_output_filename(selected)
        initial_dir = str(self.state.watchlist_path.parent) if self.state.watchlist_path else str(Path.cwd())
        path = filedialog.asksaveasfilename(
            title="保存先を選択",
            defaultextension=".txt",
            initialdir=initial_dir,
            initialfile=default_name,
            filetypes=[("Text files", "*.txt"), ("Markdown files", "*.md"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            Path(path).write_text(content + "\n", encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("保存失敗", f"ファイルを書き込めませんでした: {exc}")
            self.status_var.set(self.view_model.build_save_failed_status())
            return
        self.status_var.set(self.view_model.build_saved_status(path))


__all__ = ["FundamentalApp"]
