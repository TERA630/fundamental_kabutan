"""Normalize locally downloaded Kabutan HTML for portable use."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re

from bs4 import BeautifulSoup, Comment


HTML_SUFFIXES = {".html", ".htm"}
CODE4_RE = re.compile(r"(?<!\d)(\d{4})(?!\d)")


@dataclass(frozen=True)
class NormalizedKabutanHtml:
    """A normalized HTML document and the code inferred for it."""

    html: str
    code4: str | None
    title: str
    source_name: str | None = None

    @property
    def filename(self) -> str:
        if self.code4 is None:
            return "kabutan.html"
        return f"{self.code4}.html"


@dataclass(frozen=True)
class KabutanHtmlManifestEntry:
    source_name: str
    target_name: str | None
    code4: str | None
    title: str | None
    status: str
    message: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "source_name": self.source_name,
            "target_name": self.target_name,
            "code4": self.code4,
            "title": self.title,
            "status": self.status,
            "message": self.message,
        }


@dataclass(frozen=True)
class KabutanHtmlNormalizationResult:
    output_dir: Path
    html_dir: Path
    manifest_path: Path
    entries: tuple[KabutanHtmlManifestEntry, ...]

    @property
    def normalized_count(self) -> int:
        return sum(1 for entry in self.entries if entry.status == "normalized")

    @property
    def skipped_count(self) -> int:
        return sum(1 for entry in self.entries if entry.status != "normalized")


class KabutanHtmlNormalizer:
    """Build a minimal, UTF-8 Kabutan HTML document from a downloaded page."""

    def normalize_html(
        self,
        html: str,
        *,
        source_name: str | None = None,
        code4: str | None = None,
    ) -> NormalizedKabutanHtml:
        resolved_code4 = self.resolve_code4(html, source_name=source_name, code4=code4)
        title = resolved_code4 or "kabutan"
        body_html = self.extract_clean_body_html(html)
        normalized_html = self.build_document(title=title, body_html=body_html)
        return NormalizedKabutanHtml(
            html=normalized_html,
            code4=resolved_code4,
            title=title,
            source_name=source_name,
        )

    def normalize_file(self, path: Path, *, code4: str | None = None) -> NormalizedKabutanHtml:
        return self.normalize_html(self.read_html_file(path), source_name=path.name, code4=code4)

    def normalize_directory(self, source_dir: Path, output_dir: Path) -> KabutanHtmlNormalizationResult:
        source_dir = source_dir.resolve()
        output_dir = output_dir.resolve()
        html_dir = output_dir / "html"
        html_dir.mkdir(parents=True, exist_ok=True)

        used_names: set[str] = set()
        entries: list[KabutanHtmlManifestEntry] = []
        for source_path in self.iter_html_files(source_dir):
            try:
                normalized = self.normalize_file(source_path)
            except Exception as exc:
                entries.append(
                    KabutanHtmlManifestEntry(
                        source_name=source_path.name,
                        target_name=None,
                        code4=None,
                        title=None,
                        status="skipped",
                        message=f"HTML読み込み失敗: {exc}",
                    )
                )
                continue

            if normalized.code4 is None:
                entries.append(
                    KabutanHtmlManifestEntry(
                        source_name=source_path.name,
                        target_name=None,
                        code4=None,
                        title=normalized.title,
                        status="skipped",
                        message="4桁コードを推定できませんでした",
                    )
                )
                continue

            target_name = self.build_unique_filename(normalized.filename, used_names)
            (html_dir / target_name).write_text(normalized.html, encoding="utf-8")
            entries.append(
                KabutanHtmlManifestEntry(
                    source_name=source_path.name,
                    target_name=target_name,
                    code4=normalized.code4,
                    title=normalized.title,
                    status="normalized",
                )
            )

        manifest_path = output_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "source_dir": str(source_dir),
                    "html_dir": str(html_dir),
                    "entries": [entry.to_dict() for entry in entries],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return KabutanHtmlNormalizationResult(
            output_dir=output_dir,
            html_dir=html_dir,
            manifest_path=manifest_path,
            entries=tuple(entries),
        )

    @staticmethod
    def read_html_file(path: Path) -> str:
        data = path.read_bytes()
        for encoding in ("utf-8", "utf-8-sig", "cp932"):
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue
        return data.decode("utf-8", errors="replace")

    @staticmethod
    def iter_html_files(source_dir: Path) -> tuple[Path, ...]:
        return tuple(
            sorted(
                path
                for path in source_dir.iterdir()
                if path.is_file() and path.suffix.lower() in HTML_SUFFIXES
            )
        )

    @staticmethod
    def build_unique_filename(filename: str, used_names: set[str]) -> str:
        path = Path(filename)
        candidate = path.name
        index = 2
        while candidate.lower() in used_names:
            candidate = f"{path.stem}-{index}{path.suffix}"
            index += 1
        used_names.add(candidate.lower())
        return candidate

    @staticmethod
    def resolve_code4(html: str, *, source_name: str | None = None, code4: str | None = None) -> str | None:
        if code4 is not None:
            matched = CODE4_RE.search(code4)
            if matched is not None:
                return matched.group(1)

        if source_name:
            matched = CODE4_RE.search(Path(source_name).stem)
            if matched is not None:
                return matched.group(1)

        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.get_text(" ", strip=True) if soup.title is not None else ""
        matched = CODE4_RE.search(title)
        if matched is not None:
            return matched.group(1)

        text = soup.get_text(" ", strip=True)
        matched = CODE4_RE.search(text)
        if matched is not None:
            return matched.group(1)
        return None

    @staticmethod
    def extract_clean_body_html(html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        body = soup.body if soup.body is not None else soup

        for node in body.find_all(["script", "style", "noscript", "iframe"]):
            node.decompose()
        for comment in body.find_all(string=lambda value: isinstance(value, Comment)):
            comment.extract()

        return "\n".join(str(child).strip() for child in body.contents if str(child).strip())

    @staticmethod
    def build_document(*, title: str, body_html: str) -> str:
        return "\n".join(
            [
                "<!doctype html>",
                '<html lang="ja">',
                "<head>",
                '<meta charset="utf-8">',
                f"<title>{title}</title>",
                "</head>",
                "<body>",
                body_html,
                "</body>",
                "</html>",
                "",
            ]
        )


__all__ = [
    "HTML_SUFFIXES",
    "KabutanHtmlManifestEntry",
    "KabutanHtmlNormalizationResult",
    "NormalizedKabutanHtml",
    "KabutanHtmlNormalizer",
]
