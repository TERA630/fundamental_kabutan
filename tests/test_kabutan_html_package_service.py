import json
import zipfile
from pathlib import Path

from app.services.kabutan_html_package_service import KabutanHtmlPackageService


def test_build_package_normalizes_html_and_writes_zip(tmp_path: Path):
    source_dir = tmp_path / "source"
    output_dir = tmp_path / "package"
    source_dir.mkdir()
    (source_dir / "toyota_7203.html").write_text(
        "<html><head><title>トヨタ【7203】</title></head><body><script>bad</script><div>業績</div></body></html>",
        encoding="utf-8",
    )
    (source_dir / "unknown.html").write_text("<html><body>コードなし</body></html>", encoding="utf-8")

    result = KabutanHtmlPackageService().build_package(source_dir=source_dir, output_dir=output_dir)

    assert result.normalized_count == 1
    assert result.skipped_count == 1
    assert result.html_dir == output_dir.resolve() / "html"
    assert result.manifest_path == output_dir.resolve() / "manifest.json"
    assert result.zip_path == output_dir / "kabutan_html_package.zip"
    assert (output_dir / "html" / "7203.html").exists()

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["entries"][0]["code4"] == "7203"
    assert manifest["entries"][1]["status"] == "skipped"

    with zipfile.ZipFile(result.zip_path) as archive:
        names = archive.namelist()
        assert names == ["manifest.json", "html/7203.html"]
        assert "<title>7203</title>" in archive.read("html/7203.html").decode("utf-8")
        assert "bad" not in archive.read("html/7203.html").decode("utf-8")


def test_write_zip_includes_only_normalized_html(tmp_path: Path):
    source_dir = tmp_path / "source"
    output_dir = tmp_path / "package"
    source_dir.mkdir()
    (source_dir / "7203.html").write_text("<html><body>7203</body></html>", encoding="utf-8")

    result = KabutanHtmlPackageService().build_package(
        source_dir=source_dir,
        output_dir=output_dir,
        zip_name="custom.zip",
    )

    assert result.zip_path == output_dir / "custom.zip"
    with zipfile.ZipFile(result.zip_path) as archive:
        assert archive.namelist() == ["manifest.json", "html/7203.html"]
