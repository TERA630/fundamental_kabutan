"""Workflow for resolving uploaded Kabutan HTML packages."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from app.data.file_cache import FileCache
from app.services.kabutan_html_package_service import (
    KabutanHtmlPackageImportResult,
    KabutanHtmlPackageInspectionResult,
    KabutanHtmlPackageResult,
    KabutanHtmlPackageService,
)

WEB_KABUTAN_IMPORTED_PACKAGE_DIR_NAME = "web_imported_kabutan_html_package"


@dataclass(frozen=True)
class KabutanPackageResolution:
    html_dir: Path
    signature: tuple[int, str]
    imported: bool


class KabutanPackageWorkflow:
    def __init__(
        self,
        *,
        file_cache: FileCache,
        package_service: KabutanHtmlPackageService,
        save_kabutan_html_dir_cache: Callable[[Path], None],
    ):
        self.file_cache = file_cache
        self.package_service = package_service
        self.save_kabutan_html_dir_cache = save_kabutan_html_dir_cache

    def build_file_signature(self, path: Path) -> tuple[int, str]:
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        return (path.stat().st_size, digest.hexdigest()[:16])

    def import_output_dir_for_signature(self, signature: tuple[int, str]) -> Path:
        size, digest = signature
        return self.file_cache.base_dir / WEB_KABUTAN_IMPORTED_PACKAGE_DIR_NAME / f"{size}_{digest}"

    def html_dir_ready(self, html_dir: Path) -> bool:
        return html_dir.exists() and html_dir.is_dir() and any(html_dir.glob("*.html"))

    def build_package(
        self,
        *,
        source_dir: Path,
        output_dir: Path | None = None,
    ) -> KabutanHtmlPackageResult:
        return self.package_service.build_package(
            source_dir=source_dir,
            output_dir=output_dir or (self.file_cache.base_dir / "kabutan_html_package"),
        )

    def import_package(self, *, zip_path: Path, output_dir: Path) -> KabutanHtmlPackageImportResult:
        return self.package_service.import_package(zip_path=zip_path, output_dir=output_dir)

    def import_package_to_default_dir(
        self,
        *,
        zip_path: Path,
        output_dir: Path | None = None,
    ) -> KabutanHtmlPackageImportResult:
        return self.import_package(
            zip_path=zip_path,
            output_dir=output_dir or (self.file_cache.base_dir / "kabutan_html_imported_package"),
        )

    def inspect_package(self, *, zip_path: Path) -> KabutanHtmlPackageInspectionResult:
        return self.package_service.inspect_package(zip_path=zip_path)

    def resolve_imported_package(
        self,
        *,
        zip_path: Path,
        current_signature: tuple[int, str] | tuple[int, int] | None,
        current_html_dir: Path | None,
    ) -> KabutanPackageResolution:
        if not zip_path.exists() or not zip_path.is_file():
            raise ValueError("アップロード済みの株探HTMLパッケージZipが見つかりません。")

        signature = self.build_file_signature(zip_path)
        if (
            current_signature == signature
            and current_html_dir is not None
            and self.html_dir_ready(current_html_dir)
        ):
            return KabutanPackageResolution(
                html_dir=current_html_dir,
                signature=signature,
                imported=False,
            )

        output_dir = self.import_output_dir_for_signature(signature)
        html_dir = output_dir / "html"
        if self.html_dir_ready(html_dir):
            self.save_kabutan_html_dir_cache(html_dir)
            return KabutanPackageResolution(
                html_dir=html_dir,
                signature=signature,
                imported=False,
            )

        result = self.import_package(zip_path=zip_path, output_dir=output_dir)
        self.save_kabutan_html_dir_cache(result.html_dir)
        return KabutanPackageResolution(
            html_dir=result.html_dir,
            signature=signature,
            imported=True,
        )


__all__ = [
    "KabutanHtmlPackageImportResult",
    "KabutanHtmlPackageInspectionResult",
    "KabutanHtmlPackageResult",
    "KabutanPackageResolution",
    "KabutanPackageWorkflow",
    "WEB_KABUTAN_IMPORTED_PACKAGE_DIR_NAME",
]
