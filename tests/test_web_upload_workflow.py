from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.data.file_cache import FileCache
from app.services.web_upload_workflow import WebUploadWorkflow


class UploadedFile:
    def __init__(self, filename: str, data: bytes):
        self.filename = filename
        self.data = data

    def save(self, path: Path) -> None:
        path.write_bytes(self.data)


def test_load_uploaded_watchlist_saves_cache_file(tmp_path: Path):
    workflow = WebUploadWorkflow(file_cache=FileCache(base_dir=tmp_path / "cache"))
    data = "トヨタ (7203)\n任天堂,7974\n".encode("cp932")

    entries, path = workflow.load_uploaded_watchlist(data)

    assert entries == [("トヨタ", "7203"), ("任天堂", "7974")]
    assert path == tmp_path / "cache" / "web_uploaded_watchlist.md"
    assert path.read_bytes() == data


def test_save_uploaded_kabutan_html_dir_filters_and_dedupes(tmp_path: Path):
    workflow = WebUploadWorkflow(file_cache=FileCache(base_dir=tmp_path / "cache"))

    html_dir = workflow.save_uploaded_kabutan_html_dir(
        [
            UploadedFile("kabutan/7203.html", b"one"),
            UploadedFile("other/7203.html", b"two"),
            UploadedFile("kabutan/readme.txt", b"skip"),
        ]
    )

    assert (html_dir / "7203.html").read_bytes() == b"one"
    assert (html_dir / "7203_2.html").read_bytes() == b"two"
    assert not (html_dir / "readme.txt").exists()


def test_save_uploaded_kabutan_html_dir_rejects_missing_html(tmp_path: Path):
    workflow = WebUploadWorkflow(file_cache=FileCache(base_dir=tmp_path / "cache"))

    with pytest.raises(ValueError, match="HTMLファイルが見つかりません"):
        workflow.save_uploaded_kabutan_html_dir([UploadedFile("readme.txt", b"skip")])


def test_save_uploaded_kabutan_html_package_requires_zip(tmp_path: Path):
    workflow = WebUploadWorkflow(file_cache=FileCache(base_dir=tmp_path / "cache"))

    with pytest.raises(ValueError, match="Zipファイル"):
        workflow.save_uploaded_kabutan_html_package(SimpleNamespace(filename="package.txt"))

    path = workflow.save_uploaded_kabutan_html_package(UploadedFile("package.zip", b"zip"))

    assert path == tmp_path / "cache" / "web_uploaded_kabutan_html_package.zip"
    assert path.read_bytes() == b"zip"
