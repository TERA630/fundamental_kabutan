from app.domain.usecases.watchlist_path import ResolveWatchlistPathUseCase


class InaccessiblePath:
    def exists(self):
        raise PermissionError("access denied")

    def is_file(self):
        raise AssertionError("is_file should not be called when exists raises")


def test_resolve_watchlist_path_returns_missing_when_cached_path_is_inaccessible():
    resolved = ResolveWatchlistPathUseCase().fetch_resolved_watchlist_path(InaccessiblePath())

    assert resolved.status == "missing"
    assert resolved.file_path is None
    assert resolved.message == "前回の監視銘柄ファイルにアクセスできません。再選択してください。"
