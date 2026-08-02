"""Tests for the importer plugin framework."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import pytest

from profile_intelligence.core.exceptions import PluginError
from profile_intelligence.infrastructure.importers.base import (
    ImporterPlugin,
    ImportResult,
)
from profile_intelligence.infrastructure.importers.profile_importer import (
    ProfileImporter,
)
from profile_intelligence.infrastructure.importers.registry import ImporterRegistry


class DummyCsvImporter(ImporterPlugin):
    name: ClassVar[str] = "dummy_csv"
    description: ClassVar[str] = "Test CSV importer"
    supported_extensions: ClassVar[tuple[str, ...]] = (".csv",)

    def can_handle(self, path: str | Path) -> bool:
        return self.matches_extension(path)

    def import_file(self, path: str | Path, **options: object) -> ImportResult:
        resolved = self.validate_path(path)
        lines = resolved.read_text(encoding="utf-8").splitlines()
        return ImportResult(
            success=True,
            records_read=len(lines),
            records_imported=max(len(lines) - 1, 0),
        )


class MarkerProfileImporter(ProfileImporter):
    name: ClassVar[str] = "marker_demo"
    description: ClassVar[str] = "ProfileImporter with source marker"
    supported_extensions: ClassVar[tuple[str, ...]] = (".csv",)
    source_markers: ClassVar[tuple[str, ...]] = ("marker",)
    require_source_marker: ClassVar[bool] = True

    def parse_profiles(self, path: Path, **options: object):
        return [{"name": "Ada"}], 0


def test_register_and_list() -> None:
    registry = ImporterRegistry()
    registry.register(DummyCsvImporter())
    plugins = registry.list_plugins()
    assert len(plugins) == 1
    assert registry.get("dummy_csv").name == "dummy_csv"


def test_duplicate_registration_raises() -> None:
    registry = ImporterRegistry()
    registry.register(DummyCsvImporter())
    with pytest.raises(PluginError, match="already registered"):
        registry.register(DummyCsvImporter())


def test_find_handler(tmp_path: Path) -> None:
    csv_file = tmp_path / "sample.csv"
    csv_file.write_text("name\nAda\n", encoding="utf-8")
    registry = ImporterRegistry()
    registry.register(DummyCsvImporter())
    handler = registry.find_handler(csv_file)
    assert handler is not None
    result = handler.import_file(csv_file)
    assert result.success
    assert result.records_read == 2
    assert result.records_imported == 1


def test_discover_directory(tmp_path: Path) -> None:
    plugin_src = tmp_path / "sample_plugin.py"
    plugin_src.write_text(
        """
from typing import Any, ClassVar
from profile_intelligence.domain.interfaces.importers import ImporterPlugin
from profile_intelligence.domain.value_objects.importing import ImportResult

class ExternalImporter(ImporterPlugin):
    name: ClassVar[str] = "external_demo"
    description: ClassVar[str] = "Loaded from directory"
    supported_extensions: ClassVar[tuple[str, ...]] = (".txt",)

    def can_handle(self, path):
        return self.matches_extension(path)

    def import_file(self, path, **options: object) -> ImportResult:
        return ImportResult(success=True)
""",
        encoding="utf-8",
    )
    registry = ImporterRegistry()
    count = registry.discover_directory(tmp_path)
    assert count == 1
    assert registry.get("external_demo").description == "Loaded from directory"


def test_discover_plugin_packages(tmp_path: Path) -> None:
    package_dir = tmp_path / "sitepack"
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text(
        "from sitepack.importer import SitePackImporter\n",
        encoding="utf-8",
    )
    (package_dir / "importer.py").write_text(
        """
from typing import ClassVar
from profile_intelligence.domain.interfaces.importers import ImporterPlugin
from profile_intelligence.domain.value_objects.importing import ImportResult

class SitePackImporter(ImporterPlugin):
    name: ClassVar[str] = "sitepack"
    description: ClassVar[str] = "Package plugin"
    supported_extensions: ClassVar[tuple[str, ...]] = (".json",)

    def can_handle(self, path):
        return self.matches_extension(path)

    def import_file(self, path, **options: object) -> ImportResult:
        return ImportResult(success=True)
""",
        encoding="utf-8",
    )
    registry = ImporterRegistry()
    count = registry.discover_directory(tmp_path)
    assert count == 1
    assert registry.get("sitepack").description == "Package plugin"


def test_repo_plugin_packages_discoverable() -> None:
    repo_plugins = Path(__file__).resolve().parents[1] / "plugins"
    registry = ImporterRegistry()
    count = registry.discover_directory(repo_plugins)
    assert count >= 4
    names = {plugin.name for plugin in registry.list_plugins()}
    assert {"eurogirls", "eros", "custom", "newwebsite"}.issubset(names)
    assert all(
        isinstance(plugin, ProfileImporter) for plugin in registry.list_plugins()
    )


def test_profile_importer_source_markers(tmp_path: Path) -> None:
    plugin = MarkerProfileImporter()
    plain = tmp_path / "people.csv"
    marked = tmp_path / "marker_people.csv"
    plain.write_text("name\nAda\n", encoding="utf-8")
    marked.write_text("name\nAda\n", encoding="utf-8")

    assert plugin.can_handle(plain) is False
    assert plugin.can_handle(marked) is True
    result = plugin.import_file(marked)
    assert result.success
    assert result.records[0]["name"] == "Ada"
    assert result.metadata["plugin"] == "marker_demo"


def test_profile_importer_not_auto_registered() -> None:
    import types

    module = types.ModuleType("fake_profile_importer_module")
    module.ProfileImporter = ProfileImporter  # type: ignore[attr-defined]
    registry = ImporterRegistry()
    count = registry._register_plugins_from_module(module)
    assert count == 0
    assert registry.list_plugins() == ()


def test_import_result_failure() -> None:
    result = ImportResult.failure("nope", records_read=3)
    assert result.success is False
    assert result.errors == ("nope",)
    assert result.records_read == 3


def test_discover_builtin_plugins() -> None:
    registry = ImporterRegistry()
    count = registry.discover_builtin()
    assert count == 3
    names = {plugin.name for plugin in registry.list_plugins()}
    assert names == {"csv", "excel", "webarchive"}
