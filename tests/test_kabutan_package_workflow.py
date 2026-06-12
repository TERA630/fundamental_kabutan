from pathlib import Path

from app.data.file_cache import FileCache
from app.services.kabutan_package_workflow import KabutanPackageWorkflow


class FakePackageService:
    def __init__(self):
        self.calls = []

    def build_package(self, *, source_dir, output_dir):
        self.calls.append(("build", source_dir, output_dir))
        return output_dir

    def import_package(self, *, zip_path, output_dir):
        self.calls.append(("import", zip_path, output_dir))
        return output_dir

    def inspect_package(self, *, zip_path):
        self.calls.append(("inspect", zip_path))
        return zip_path


def build_workflow(tmp_path: Path, service: FakePackageService) -> KabutanPackageWorkflow:
    return KabutanPackageWorkflow(
        file_cache=FileCache(base_dir=tmp_path / "cache"),
        package_service=service,
        save_kabutan_html_dir_cache=lambda _path: None,
    )


def test_build_package_uses_default_output_dir(tmp_path):
    service = FakePackageService()
    workflow = build_workflow(tmp_path, service)
    source_dir = tmp_path / "source"

    result = workflow.build_package(source_dir=source_dir)

    assert result == tmp_path / "cache" / "kabutan_html_package"
    assert service.calls == [("build", source_dir, tmp_path / "cache" / "kabutan_html_package")]


def test_import_package_to_default_dir_uses_default_output_dir(tmp_path):
    service = FakePackageService()
    workflow = build_workflow(tmp_path, service)
    zip_path = tmp_path / "package.zip"

    result = workflow.import_package_to_default_dir(zip_path=zip_path)

    assert result == tmp_path / "cache" / "kabutan_html_imported_package"
    assert service.calls == [("import", zip_path, tmp_path / "cache" / "kabutan_html_imported_package")]


def test_inspect_package_delegates_to_package_service(tmp_path):
    service = FakePackageService()
    workflow = build_workflow(tmp_path, service)
    zip_path = tmp_path / "package.zip"

    assert workflow.inspect_package(zip_path=zip_path) == zip_path
    assert service.calls == [("inspect", zip_path)]
