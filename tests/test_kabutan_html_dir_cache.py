from pathlib import Path

from app.data.file_cache import FileCache
from app.domain.usecases.kabutan_html_dir import ResolveKabutanHtmlDirUseCase


def test_file_cache_can_save_and_fetch_kabutan_html_dir(tmp_path: Path):
    cache = FileCache(base_dir=tmp_path / "cache")
    target_dir = tmp_path / "kabutan"
    target_dir.mkdir()

    cache.save_kabutan_html_dir_cache(target_dir)

    fetched = cache.fetch_kabutan_html_dir_cache()
    assert fetched == target_dir.resolve()


def test_file_cache_can_save_and_fetch_kabutan_package_zip(tmp_path: Path):
    cache = FileCache(base_dir=tmp_path / "cache")
    zip_path = tmp_path / "kabutan_html_package.zip"
    zip_path.write_bytes(b"zip")

    cache.save_kabutan_package_zip_cache(zip_path)

    fetched = cache.fetch_kabutan_package_zip_cache()
    assert fetched == zip_path.resolve()


def test_file_cache_can_clear_kabutan_package_zip(tmp_path: Path):
    cache = FileCache(base_dir=tmp_path / "cache")
    zip_path = tmp_path / "kabutan_html_package.zip"
    zip_path.write_bytes(b"zip")
    cache.save_kabutan_package_zip_cache(zip_path)

    cache.clear_kabutan_package_zip_cache()

    assert cache.fetch_kabutan_package_zip_cache() is None


def test_resolve_kabutan_html_dir_returns_ok_for_existing_dir(tmp_path: Path):
    target_dir = tmp_path / "kabutan"
    target_dir.mkdir()

    usecase = ResolveKabutanHtmlDirUseCase()
    resolved = usecase.fetch_resolved_kabutan_html_dir(target_dir)

    assert resolved.status == "ok"
    assert resolved.dir_path == target_dir


def test_resolve_kabutan_html_dir_returns_missing_for_deleted_dir(tmp_path: Path):
    deleted_dir = tmp_path / "kabutan"

    usecase = ResolveKabutanHtmlDirUseCase()
    resolved = usecase.fetch_resolved_kabutan_html_dir(deleted_dir)

    assert resolved.status == "missing"
    assert resolved.dir_path is None


def test_file_cache_can_save_and_fetch_watchlist_path(tmp_path: Path):
    cache = FileCache(base_dir=tmp_path / "cache")
    target_file = tmp_path / "watchlist.md"
    target_file.write_text("トヨタ (7203)\n", encoding="utf-8")

    cache.save_watchlist_path_cache(target_file)

    fetched = cache.fetch_watchlist_path_cache()
    assert fetched == target_file.resolve()


