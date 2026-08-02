"""Tests for the Importer → Database pipeline stages."""

from __future__ import annotations

from pathlib import Path

from profile_intelligence.bootstrap import build_container
from profile_intelligence.importers.base import ImportResult
from profile_intelligence.services.application import ApplicationService
from profile_intelligence.services.import_service import ImportService
from profile_intelligence.services.profile_service import ProfileService


def test_importer_then_database_stages(temp_root: Path) -> None:
    container = build_container(root_dir=temp_root)
    app = container.resolve(ApplicationService)
    app.start()

    csv_path = temp_root / "stage_people.csv"
    csv_path.write_text(
        "name,email\nAda Lovelace,ada@example.com\n",
        encoding="utf-8",
    )

    service = container.resolve(ImportService)
    plugin = service.resolve_importer(csv_path)
    assert plugin.name == "csv"

    parse_result = service.run_importer(plugin, csv_path)
    assert parse_result.success
    assert parse_result.records_read == 1

    summary = service.write_to_database(
        parse_result,
        path=csv_path,
        plugin_name=plugin.name,
        source="csv",
    )
    assert summary.created == 1
    assert summary.written == 1
    assert container.resolve(ProfileService).count() == 1
    app.shutdown()


def test_write_to_database_from_records(temp_root: Path) -> None:
    container = build_container(root_dir=temp_root)
    app = container.resolve(ApplicationService)
    app.start()

    service = container.resolve(ImportService)
    parse_result = ImportResult.from_records(
        [{"name": "Grace Hopper", "email": "grace@example.com"}],
        metadata={"plugin": "manual"},
    )
    summary = service.write_to_database(
        parse_result,
        path=temp_root / "manual.json",
        plugin_name="manual",
        source="manual",
    )
    assert summary.success
    assert summary.created == 1
    app.shutdown()
