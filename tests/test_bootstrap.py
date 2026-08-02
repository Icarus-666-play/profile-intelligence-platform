"""Tests for composition root / application startup."""

from __future__ import annotations

from pathlib import Path

from profile_intelligence.bootstrap import build_container
from profile_intelligence.core.config import AppConfig
from profile_intelligence.database.connection import Database
from profile_intelligence.importers.registry import ImporterRegistry
from profile_intelligence.services.application import ApplicationService


def test_build_container_and_start(temp_root: Path) -> None:
    container = build_container(root_dir=temp_root)
    assert container.has(AppConfig)
    assert container.has(Database)
    assert container.has(ImporterRegistry)

    app = container.resolve(ApplicationService)
    app.start()
    assert app.is_started
    assert app.config.database_path.exists()
    assert "001" in __import__(
        "profile_intelligence.database.migrations.runner",
        fromlist=["MigrationRunner"],
    ).MigrationRunner(app.database).applied_versions()

    app.shutdown()
    assert not app.is_started
