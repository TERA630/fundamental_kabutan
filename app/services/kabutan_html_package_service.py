"""Service for building a portable Kabutan HTML package."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import zipfile

from app.domain.usecases.kabutan_html_normalizer import (
    KabutanHtmlNormalizationResult,
    KabutanHtmlNormalizer,
)


DEFAULT_PACKAGE_NAME = "kabutan_html_package.zip"


@dataclass(frozen=True)
class KabutanHtmlPackageResult:
    normalization: KabutanHtmlNormalizationResult
    zip_path: Path

    @property
    def html_dir(self) -> Path:
        return self.normalization.html_dir

    @property
    def manifest_path(self) -> Path:
        return self.normalization.manifest_path

    @property
    def normalized_count(self) -> int:
        return self.normalization.normalized_count

    @property
    def skipped_count(self) -> int:
        return self.normalization.skipped_count


class KabutanHtmlPackageService:
    """Create normalized HTML files and a zip archive for Codespaces."""

    def __init__(self, normalizer: KabutanHtmlNormalizer | None = None):
        self.normalizer = normalizer or KabutanHtmlNormalizer()

    def build_package(
        self,
        *,
        source_dir: Path,
        output_dir: Path,
        zip_name: str = DEFAULT_PACKAGE_NAME,
    ) -> KabutanHtmlPackageResult:
        normalization = self.normalizer.normalize_directory(source_dir, output_dir)
        zip_path = output_dir / zip_name
        self.write_zip(normalization=normalization, zip_path=zip_path)
        return KabutanHtmlPackageResult(normalization=normalization, zip_path=zip_path)

    @staticmethod
    def write_zip(*, normalization: KabutanHtmlNormalizationResult, zip_path: Path) -> Path:
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(normalization.manifest_path, "manifest.json")
            for html_path in sorted(normalization.html_dir.glob("*.html")):
                archive.write(html_path, f"html/{html_path.name}")
        return zip_path


__all__ = ["DEFAULT_PACKAGE_NAME", "KabutanHtmlPackageResult", "KabutanHtmlPackageService"]
