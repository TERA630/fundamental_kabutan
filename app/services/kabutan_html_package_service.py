"""Service for building a portable Kabutan HTML package."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
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


@dataclass(frozen=True)
class KabutanHtmlPackageImportResult:
    output_dir: Path
    html_dir: Path
    manifest_path: Path | None
    html_count: int


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

    def import_package(self, *, zip_path: Path, output_dir: Path) -> KabutanHtmlPackageImportResult:
        output_dir = output_dir.resolve()
        if output_dir.exists():
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(zip_path) as archive:
                for member in archive.infolist():
                    if member.is_dir():
                        continue
                    target_path = self._resolve_zip_member(output_dir, member.filename)
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(member) as source, target_path.open("wb") as target:
                        shutil.copyfileobj(source, target)

            html_dir = output_dir / "html"
            if not html_dir.exists() or not html_dir.is_dir():
                raise ValueError("Zip内に html/ フォルダが見つかりません。")

            html_count = len([path for path in html_dir.iterdir() if path.is_file() and path.suffix.lower() == ".html"])
            if html_count == 0:
                raise ValueError("Zip内の html/ フォルダにHTMLファイルが見つかりません。")
        except Exception:
            if output_dir.exists():
                shutil.rmtree(output_dir)
            raise

        manifest_path = output_dir / "manifest.json"
        return KabutanHtmlPackageImportResult(
            output_dir=output_dir,
            html_dir=html_dir,
            manifest_path=manifest_path if manifest_path.exists() else None,
            html_count=html_count,
        )

    @staticmethod
    def write_zip(*, normalization: KabutanHtmlNormalizationResult, zip_path: Path) -> Path:
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(normalization.manifest_path, "manifest.json")
            for html_path in sorted(normalization.html_dir.glob("*.html")):
                archive.write(html_path, f"html/{html_path.name}")
        return zip_path

    @staticmethod
    def _resolve_zip_member(output_dir: Path, member_name: str) -> Path:
        normalized_name = member_name.replace("\\", "/")
        if normalized_name.startswith("/") or normalized_name.startswith("../") or "/../" in normalized_name:
            raise ValueError(f"Zip内に不正なパスが含まれています: {member_name}")
        target_path = (output_dir / normalized_name).resolve()
        if output_dir != target_path and output_dir not in target_path.parents:
            raise ValueError(f"Zip内に不正なパスが含まれています: {member_name}")
        return target_path


__all__ = [
    "DEFAULT_PACKAGE_NAME",
    "KabutanHtmlPackageImportResult",
    "KabutanHtmlPackageResult",
    "KabutanHtmlPackageService",
]
