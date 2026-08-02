"""Local fixtures for EuroGirls plugin tests (standalone collection)."""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml

from profile_intelligence.core.config import AppConfig
from profile_intelligence.core.config_manager import load_config
from profile_intelligence.core.logging import reset_logging

_ROOT = Path(__file__).resolve().parents[2]
for candidate in (_ROOT, _ROOT / "src", _ROOT / "plugins"):
    text = str(candidate)
    if text not in sys.path:
        sys.path.insert(0, text)


@pytest.fixture(autouse=True)
def _reset_logging_state() -> Iterator[None]:
    reset_logging()
    yield
    reset_logging()


@pytest.fixture
def temp_root(tmp_path: Path) -> Path:
    """Minimal install root with YAML config for integration tests."""
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
        "ai": {
            "enabled": False,
            "provider": None,
            "model": None,
            "base_url": None,
            "api_key": None,
        },
        "search": {"default_limit": 50, "fuzzy": True},
        "dashboard": {"refresh_seconds": 30},
        "media": {
            "root_dir": "data/media",
            "thumbnails_dir": "data/media/thumbnails",
            "hash_algorithm": "sha256",
            "thumbnail_max_size": 64,
            "thumbnail_format": "JPEG",
            "thumbnail_quality": 80,
        },
        "nightly": {
            "import_dir": "data/inbox",
            "excel_path": "exports/nightly-profiles.xlsx",
            "dashboard_path": "exports/nightly-dashboard.txt",
            "rescore": True,
            "recursive": False,
        },
        "pipeline": [
            "parser",
            "normalizer",
            "validator",
            "duplicate_detector",
            "scorer",
            "repository",
        ],
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
        yaml.safe_dump(settings), encoding="utf-8"
    )
    (config_dir / "logging.yaml").write_text(
        yaml.safe_dump(logging_cfg), encoding="utf-8"
    )
    (config_dir / "scoring.yaml").write_text(
        yaml.safe_dump(scoring_cfg), encoding="utf-8"
    )
    return tmp_path


@pytest.fixture
def app_config(temp_root: Path) -> AppConfig:
    return load_config(root_dir=temp_root)
