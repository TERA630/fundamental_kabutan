from pathlib import Path

from app.data.file_cache import FileCache
from app.services.cache_service import CacheService
from app.services.kabutan_html_dir_service import KabutanHtmlDirService
from app.services.ui_resource_workflow import UiResourceWorkflow
from app.services.watchlist_service import WatchlistService


def build_workflow(tmp_path: Path) -> UiResourceWorkflow:
    cache_service = CacheService(FileCache(base_dir=tmp_path / "cache"))
    return UiResourceWorkflow(
        cache_service=cache_service,
        watchlist_service=WatchlistService(cache_service),
        kabutan_html_dir_service=KabutanHtmlDirService(cache_service),
    )


def test_watchlist_cache_resolution_and_loading(tmp_path):
    workflow = build_workflow(tmp_path)
    watchlist_path = tmp_path / "watchlist.md"
    watchlist_path.write_text("トヨタ (7203) 商社\n任天堂,7974\n", encoding="utf-8")

    workflow.save_watchlist_path_cache(watchlist_path)
    resolved = workflow.fetch_resolved_watchlist_path()

    assert resolved.file_path == watchlist_path
    assert workflow.fetch_watchlist_entries(resolved.file_path) == [("トヨタ", "7203"), ("任天堂", "7974")]
    sector_entries = workflow.fetch_watchlist_entries_with_sectors(resolved.file_path)
    assert sector_entries[0].sectors == ("商社・資源",)
    assert sector_entries[1].sectors == ()


def test_kabutan_package_zip_cache_requires_existing_file(tmp_path):
    workflow = build_workflow(tmp_path)
    missing_zip = tmp_path / "missing.zip"

    workflow.save_kabutan_package_zip_cache(missing_zip)
    assert workflow.fetch_kabutan_package_zip_cache() is None

    zip_path = tmp_path / "package.zip"
    zip_path.write_bytes(b"zip")
    workflow.save_kabutan_package_zip_cache(zip_path)

    assert workflow.fetch_kabutan_package_zip_cache() == zip_path
    workflow.clear_kabutan_package_zip_cache()
    assert workflow.fetch_kabutan_package_zip_cache() is None
