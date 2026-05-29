"""GUI view-model: 画面表示用メッセージ/表示値の生成。"""

from __future__ import annotations


class GuiViewModel:
    """表示用文字列を生成する。"""

    @staticmethod
    def build_loaded_status(count: int) -> str:
        return f"{count}件の監視銘柄を読み込みました。"

    @staticmethod
    def build_watchlist_restored_status(count: int) -> str:
        return f"前回の監視銘柄ファイルを復元しました（{count}件）。"

    @staticmethod
    def build_selected_status() -> str:
        return "銘柄を選択しました。取得ボタンを押してください。"

    @staticmethod
    def build_missing_stock_status() -> str:
        return "先に監視銘柄ファイルと銘柄を選んでください。"

    @staticmethod
    def build_initial_status() -> str:
        return "監視銘柄ファイルを読み込んでください。"

    @staticmethod
    def build_no_stock_found_status() -> str:
        return "銘柄が見つかりませんでした。"

    @staticmethod
    def build_missing_copy_content_status() -> str:
        return "コピーするテキストがありません。"

    @staticmethod
    def build_copied_status() -> str:
        return "クリップボードにコピーしました。"

    @staticmethod
    def build_missing_save_content_status() -> str:
        return "保存するテキストがありません。"

    @staticmethod
    def build_saved_status(path: str) -> str:
        return f"保存完了: {path}"

    @staticmethod
    def build_save_failed_status() -> str:
        return "保存に失敗しました。"

    @staticmethod
    def build_fetching_status(name: str, code4: str) -> str:
        return f"取得中: {name} ({code4}) / 業績=株探(HTML優先) / 指標=yFinance"

    @staticmethod
    def build_generated_status(name: str, code4: str) -> str:
        return f"生成完了: {name} ({code4}) / 業績=株探(HTML優先) / 指標=yFinance"

    @staticmethod
    def build_cached_status(name: str, code4: str) -> str:
        return f"キャッシュ表示: {name} ({code4})"

    @staticmethod
    def build_fetch_failed_status() -> str:
        return "取得に失敗しました。"

    @staticmethod
    def build_summary_running_status() -> str:
        return "サマリ作成中です。"

    @staticmethod
    def build_summary_failed_status() -> str:
        return "サマリ作成に失敗しました。"

    @staticmethod
    def build_kabutan_dir_selected_status() -> str:
        return "株探HTMLフォルダを設定しました（出力キャッシュをクリア）。"

    @staticmethod
    def build_kabutan_dir_restore_required_status() -> str:
        return "株探HTMLフォルダが見つかりません。再選択してください。"


__all__ = ["GuiViewModel"]
