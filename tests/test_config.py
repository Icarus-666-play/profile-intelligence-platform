"""Tests for YAML configuration loading."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from profile_intelligence.core.config import ENV_LOG_LEVEL, load_config
from profile_intelligence.core.exceptions import ConfigurationError


def test_load_default_config(temp_root: Path) -> None:
    config = load_config(root_dir=temp_root)
    assert config.app.short_name == "PIP"
    assert config.app.environment == "test"
    assert config.database_path == (temp_root / "data" / "pip.sqlite3").resolve()
    assert config.logging.level == "DEBUG"


def test_local_override(temp_root: Path) -> None:
    override = {"logging": {"level": "WARNING"}, "app": {"environment": "production"}}
    (temp_root / "config" / "local.yaml").write_text(
        yaml.safe_dump(override),
        encoding="utf-8",
    )
    config = load_config(root_dir=temp_root)
    assert config.logging.level == "WARNING"
    assert config.app.environment == "production"


def test_explicit_config_path(temp_root: Path, tmp_path: Path) -> None:
    custom = tmp_path / "custom.yaml"
    custom.write_text(
        yaml.safe_dump({"search": {"default_limit": 10}}),
        encoding="utf-8",
    )
    config = load_config(custom, root_dir=temp_root)
    assert config.search.default_limit == 10


def test_env_log_level_override(
    temp_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(ENV_LOG_LEVEL, "error")
    config = load_config(root_dir=temp_root)
    assert config.logging.level == "ERROR"


def test_missing_default_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="Default configuration missing"):
        load_config(root_dir=tmp_path)


def test_ensure_directories(app_config) -> None:
    app_config.ensure_directories()
    assert app_config.data_dir.is_dir()
    assert app_config.logs_dir.is_dir()
    assert app_config.exports_dir.is_dir()
    assert app_config.plugins_dir.is_dir()


def test_invalid_yaml(temp_root: Path) -> None:
    bad = temp_root / "config" / "local.yaml"
    bad.write_text("app: [\n", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="Invalid YAML"):
        load_config(root_dir=temp_root)


def test_env_cleanup(monkeypatch: pytest.MonkeyPatch) -> None:
    # Ensure tests do not leak PIP_* into other cases unexpectedly.
    for key in list(os.environ):
        if key.startswith("PIP_"):
            monkeypatch.delenv(key, raising=False)
