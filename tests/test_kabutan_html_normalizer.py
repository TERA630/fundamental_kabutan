import json
from pathlib import Path

from app.domain.usecases.kabutan_html_normalizer import KabutanHtmlNormalizer


def test_normalize_html_extracts_body_and_sets_code_only_title():
    html = """
    <html>
      <head>
        <title>トヨタ自動車【7203】株探</title>
        <script>window.bad = true;</script>
      </head>
      <body>
        <style>.ad { display: none; }</style>
        <main><h1>決算</h1><table><tr><td>100</td></tr></table></main>
        <noscript>noise</noscript>
      </body>
    </html>
    """

    result = KabutanHtmlNormalizer().normalize_html(html, source_name="toyota.html")

    assert result.code4 == "7203"
    assert result.title == "7203"
    assert result.filename == "7203.html"
    assert "<title>7203</title>" in result.html
    assert "<main><h1>決算</h1><table><tr><td>100</td></tr></table></main>" in result.html
    assert "window.bad" not in result.html
    assert ".ad" not in result.html
    assert "noise" not in result.html


def test_normalize_html_prefers_explicit_code4_over_source_name_and_title():
    html = '<html><head><title>任天堂【7974】</title></head><body>body</body></html>'

    result = KabutanHtmlNormalizer().normalize_html(html, source_name="7203.html", code4="8058")

    assert result.code4 == "8058"
    assert result.title == "8058"
    assert result.filename == "8058.html"


def test_normalize_file_resolves_code4_from_filename(tmp_path: Path):
    path = tmp_path / "INPEX_1605_finance.html"
    path.write_text("<html><body><div>業績</div></body></html>", encoding="utf-8")

    result = KabutanHtmlNormalizer().normalize_file(path)

    assert result.code4 == "1605"
    assert result.html.startswith("<!doctype html>")
    assert "<title>1605</title>" in result.html


def test_normalize_file_accepts_cp932_saved_html(tmp_path: Path):
    path = tmp_path / "7203.html"
    path.write_bytes("<html><body><div>業績</div></body></html>".encode("cp932"))

    result = KabutanHtmlNormalizer().normalize_file(path)

    assert result.code4 == "7203"
    assert "業績" in result.html


def test_normalize_directory_writes_html_dir_and_manifest(tmp_path: Path):
    source_dir = tmp_path / "source"
    output_dir = tmp_path / "normalized"
    source_dir.mkdir()
    (source_dir / "toyota_7203.html").write_text(
        "<html><head><title>トヨタ【7203】</title></head><body><script>bad</script><div>業績</div></body></html>",
        encoding="utf-8",
    )
    (source_dir / "toyota_duplicate_7203.htm").write_text(
        "<html><body><div>重複</div></body></html>",
        encoding="utf-8",
    )
    (source_dir / "unknown.html").write_text("<html><body><div>コードなし</div></body></html>", encoding="utf-8")
    (source_dir / "readme.txt").write_text("7203", encoding="utf-8")

    result = KabutanHtmlNormalizer().normalize_directory(source_dir, output_dir)

    assert result.normalized_count == 2
    assert result.skipped_count == 1
    assert (output_dir / "html" / "7203.html").exists()
    assert (output_dir / "html" / "7203-2.html").exists()
    assert not (output_dir / "html" / "readme.html").exists()
    assert "<title>7203</title>" in (output_dir / "html" / "7203.html").read_text(encoding="utf-8")
    assert "bad" not in (output_dir / "html" / "7203.html").read_text(encoding="utf-8")

    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["version"] == 1
    assert len(manifest["entries"]) == 3
    assert manifest["entries"][0]["target_name"] == "7203.html"
    assert manifest["entries"][1]["target_name"] == "7203-2.html"
    assert manifest["entries"][2]["status"] == "skipped"
