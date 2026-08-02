"""Tests for ConfigManager."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from profile_intelligence.core.config import ConfigManager
from profile_intelligence.core.exceptions import ConfigurationError


def test_config_manager_load(temp_root: Path) -> None:
    manager = ConfigManager(root_dir=temp_root)
    assert not manager.is_loaded
    config = manager.load()
    assert manager.is_loaded
    assert config.app.short_name == "PIP"
    assert manager.settings is config
    assert manager.config_dir == temp_root / "config"


def test_config_manager_autoload(temp_root: Path) -> None:
    manager = ConfigManager(root_dir=temp_root, autoload=True)
    assert manager.is_loaded
    assert manager.config.logging.level == "DEBUG"


def test_config_manager_reload(temp_root: Path) -> None:
    manager = ConfigManager(root_dir=temp_root)
    manager.load()
    (temp_root / "config" / "logging.local.yaml").write_text(
        yaml.safe_dump({"level": "ERROR"}),
        encoding="utf-8",
    )
    reloaded = manager.reload()
    assert reloaded.logging.level == "ERROR"
    assert manager.config.logging.level == "ERROR"


def test_config_manager_get_section(temp_root: Path) -> None:
    manager = ConfigManager(root_dir=temp_root, autoload=True)
    app = manager.get("app")
    assert app.short_name == "PIP"
    with pytest.raises(ConfigurationError, match="Unknown configuration section"):
        manager.get("missing")


def test_config_manager_ensure_directories(temp_root: Path) -> None:
    manager = ConfigManager(root_dir=temp_root)
    manager.ensure_directories()
    assert manager.config.data_dir.is_dir()


def test_config_manager_in_container(temp_root: Path) -> None:
    from profile_intelligence.bootstrap import build_container
    from profile_intelligence.core.config import AppConfig

    container = build_container(root_dir=temp_root)
    assert container.has(ConfigManager)
    assert container.has(AppConfig)
    manager = container.resolve(ConfigManager)
    assert manager.settings.app.environment == "test"
