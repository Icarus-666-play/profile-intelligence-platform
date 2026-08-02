"""Tests for composition root / application startup."""

from __future__ import annotations

from pathlib import Path

from profile_intelligence.application.use_cases.application import ApplicationService
from profile_intelligence.bootstrap import build_container
from profile_intelligence.core.config import AppConfig
from profile_intelligence.core.config_manager import ConfigManager
from profile_intelligence.infrastructure.database.connection import Database
from profile_intelligence.infrastructure.importers.registry import ImporterRegistry


def test_build_container_and_start(temp_root: Path) -> None:
    container = build_container(root_dir=temp_root)
    assert container.has(ConfigManager)
    assert container.has(AppConfig)
    assert container.has(Database)
    assert container.has(ImporterRegistry)

    app = container.resolve(ApplicationService)
    app.start()
    assert app.is_started
    assert app.config.database_path.exists()
    from profile_intelligence.infrastructure.database.migrate import MigrationRunner

    assert "001" in MigrationRunner(app.database).applied_versions()

    app.shutdown()
    assert not app.is_started
