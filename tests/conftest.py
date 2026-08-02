"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml

from profile_intelligence.core.config import AppConfig
from profile_intelligence.core.config_manager import load_config
from profile_intelligence.core.logging import reset_logging
from profile_intelligence.infrastructure.database.connection import (
    Database,
    create_database,
)
from profile_intelligence.infrastructure.database.migrate import run_migrations


@pytest.fixture(autouse=True)
def _reset_logging_state() -> Iterator[None]:
    reset_logging()
    yield
    reset_logging()


@pytest.fixture
def temp_root(tmp_path: Path) -> Path:
    """Create a minimal install root with split config files for tests."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    settings = {
        "app": {
            "name": "Profile Intelligence Platform",
            "short_name": "PIP",
            "version": "0.1.0",
            "environment": "test",
        },
        "paths": {
            "data_dir": "data",
            "database_file": "data/pip.sqlite3",
            "logs_dir": "logs",
            "exports_dir": "exports",
            "plugins_dir": "plugins",
        },
        "database": {
            "echo_sql": False,
            "timeout_seconds": 5.0,
            "check_same_thread": False,
            "foreign_keys": True,
        },
        "importers": {"auto_discover": True, "enabled": []},
        "excel": {"default_sheet_name": "Profiles", "date_format": "YYYY-MM-DD"},
        "ai": {"enabled": False, "provider": None, "model": None},
        "search": {"default_limit": 50, "fuzzy": True},
        "dashboard": {"refresh_seconds": 30},
    }
    logging_cfg = {
        "level": "DEBUG",
        "console": False,
        "file": True,
        "files": {
            "application": "application.log",
            "import": "import.log",
            "errors": "errors.log",
        },
        "max_bytes": 1_000_000,
        "backup_count": 1,
    }
    scoring_cfg = {
        "method": "completeness",
        "max_score": 100,
        "weights": {
            "display_name": 25,
            "email": 20,
            "phone": 10,
            "title": 10,
            "organization": 10,
            "location": 10,
            "tags": 5,
            "notes": 5,
            "external_id": 5,
        },
    }

    (config_dir / "settings.yaml").write_text(
        yaml.safe_dump(settings),
        encoding="utf-8",
    )
    (config_dir / "logging.yaml").write_text(
        yaml.safe_dump(logging_cfg),
        encoding="utf-8",
    )
    (config_dir / "scoring.yaml").write_text(
        yaml.safe_dump(scoring_cfg),
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def app_config(temp_root: Path) -> AppConfig:
    return load_config(root_dir=temp_root)


@pytest.fixture
def database(app_config: AppConfig) -> Iterator[Database]:
    db = create_database(app_config)
    run_migrations(db)
    yield db
    db.disconnect()
