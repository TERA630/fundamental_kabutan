"""GUI layer: Tkinter application wiring and event handling."""

from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from app.gui_controller import FundamentalGuiController
from app.gui_state import (
    GuiState,
    build_default_output_filename,
    build_output_cache_key,
    build_stock_choices,
    current_date_iso,
    get_selected_stock,
    should_rotate_output_cache,
)
from app.gui_view import FundamentalView
from app.gui_view_model import GuiViewModel


class FundamentalApp:
    """GUI層: 画面イベント連携と状態遷移を担当。"""

    def __init__(self, master: tk.Tk):
        self.master = master
        self.master.title("ファンダメンタル評価 v8（株探/yFinanceベース）")
        self.master.geometry("1040x820")

        self.state = GuiState()
        self.controller = FundamentalGuiController()

        self.path_var = tk.StringVar(value="監視銘柄ファイル未選択")
        self.kabutan_dir_var = tk.StringVar(value="株探HTMLフォルダ未選択")
        self.stock_var = tk.StringVar()
        self.status_var = tk.StringVar(value=GuiViewModel.build_initial_status())

        self.view_model = GuiViewModel()
        self.view = FundamentalView(
            self.master,
            self.path_var,
            self.stock_var,
            self.status_var,
            self.kabutan_dir_var,
        )
        self.view.build_ui(
            on_open=self.open_watchlist,
            on_select=self.on_stock_selected,
            on_fetch=self.generate_text,
            on_copy=self.copy_text,
            on_save=self.save_text,
            on_open_kabutan_dir=self.open_kabutan_html_dir,
        )
        self.state.output_cache = self.controller.fetch_output_cache_for_today()
        self.state.output_cache_date = current_date_iso()
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
            watchlist = self.controller.fetch_watchlist_entries(Path(path))
        except Exception as exc:
            messagebox.showerror("読込失敗", str(exc))
            return

        self.state.watchlist_path = Path(path)
        self.controller.save_watchlist_path_cache(self.state.watchlist_path)
        self.state.watchlist = watchlist
        self.state.output_cache.clear()
        self.state.output_cache_date = current_date_iso()
        self.controller.save_output_cache_for_today(self.state.output_cache)
        self.path_var.set(str(self.state.watchlist_path))
        self._populate_stock_choices()

    def _restore_watchlist(self) -> None:
        resolved = self.controller.fetch_resolved_watchlist_path()
        if resolved.status != "ok" or resolved.file_path is None:
            return
        try:
            watchlist = self.controller.fetch_watchlist_entries(resolved.file_path)
        except Exception:
            return
        self.state.watchlist_path = resolved.file_path
        self.state.watchlist = watchlist
        self.path_var.set(str(resolved.file_path))
        self._populate_stock_choices()
        self.status_var.set(self.view_model.build_watchlist_restored_status(len(watchlist)))

    def open_kabutan_html_dir(self):
        path = filedialog.askdirectory(title="株探HTML保存フォルダを選択")
        if not path:
            return
        self.state.kabutan_html_dir = Path(path)
        self.controller.save_kabutan_html_dir_cache(self.state.kabutan_html_dir)
        self.state.output_cache.clear()
        self.state.output_cache_date = current_date_iso()
        self.controller.save_output_cache_for_today(self.state.output_cache)
        self.kabutan_dir_var.set(str(self.state.kabutan_html_dir))
        self.status_var.set(self.view_model.build_kabutan_dir_selected_status())

    def _restore_kabutan_html_dir(self) -> None:
        resolved = self.controller.fetch_resolved_kabutan_html_dir()
        if resolved.status == "ok" and resolved.dir_path is not None:
            self.state.kabutan_html_dir = resolved.dir_path
            self.kabutan_dir_var.set(str(resolved.dir_path))
            self.status_var.set(resolved.message)

    def _populate_stock_choices(self) -> None:
        values, mapping = build_stock_choices(self.state.watchlist)
        self.state.display_to_code = mapping
        self.view.set_stock_choices(values)

        if values:
            self.stock_var.set(values[0])
            self.status_var.set(self.view_model.build_loaded_status(len(values)))
        else:
            self.stock_var.set("")
            self.view.clear_text()
            self.status_var.set(self.view_model.build_no_stock_found_status())

    def on_stock_selected(self, _event=None):
        self.status_var.set(self.view_model.build_selected_status())

    def selected_stock(self) -> tuple[str, str] | None:
        return get_selected_stock(self.state.display_to_code, self.stock_var.get())

    def _require_selected_stock(self) -> tuple[str, str] | None:
        selected = self.selected_stock()
        if selected is None:
            self.status_var.set(self.view_model.build_missing_stock_status())
            return None
        return selected

    def _render_output(self, output: str, status: str):
        self.view.render_output(output)
        self.set_busy(False, status)

    def _handle_fetch_error(self, message: str):
        self.set_busy(False, self.view_model.build_fetch_failed_status())
        messagebox.showerror("取得失敗", message)

    def _fetch_worker(self, name: str, code4: str, cache_key: str):
        try:
            output = self.controller.fetch_analysis_output(
                name=name,
                code4=code4,
                output_cache=self.state.output_cache,
                output_cache_key=cache_key,
                kabutan_html_dir=self.state.kabutan_html_dir,
            )
            self.controller.save_output_cache_for_today(self.state.output_cache)
            self.master.after(0, lambda: self._render_output(output, self.view_model.build_generated_status(name, code4)))
        except Exception as exc:
            self.master.after(0, lambda msg=str(exc): self._handle_fetch_error(msg))

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
        if not should_rotate_output_cache(self.state.output_cache_date):
            return
        self.state.output_cache.clear()
        self.state.output_cache_date = current_date_iso()
        self.controller.save_output_cache_for_today(self.state.output_cache)

    def _start_fetch_thread(self, name: str, code4: str, cache_key: str) -> None:
        self.set_busy(True, self.view_model.build_fetching_status(name, code4))
        thread = threading.Thread(target=self._fetch_worker, args=(name, code4, cache_key), daemon=True)
        thread.start()

    def generate_text(self):
        if self.state.is_fetching:
            return

        self._rotate_output_cache_if_needed()

        selected = self._require_selected_stock()
        if selected is None:
            return

        name, code4 = selected
        if not self._require_kabutan_html_dir():
            return

        cache_key = build_output_cache_key(code4, self.state.kabutan_html_dir)
        if self._render_cached_output(name, code4, cache_key):
            return

        self._start_fetch_thread(name, code4, cache_key)

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
