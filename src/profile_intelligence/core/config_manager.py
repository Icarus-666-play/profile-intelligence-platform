"""Configuration manager for split YAML settings."""

from __future__ import annotations

import os
from pathlib import Path

from profile_intelligence.core.config import (
    ENV_CONFIG_PATH,
    LOGGING_FILENAME,
    SCORING_FILENAME,
    SETTINGS_FILENAME,
    AppConfig,
    _apply_env_overrides,
    _build_config,
    _deep_merge,
    _load_yaml,
    _merge_file_pair,
    _normalize_logging_raw,
    _normalize_scoring_raw,
    _repo_root,
)
from profile_intelligence.core.exceptions import ConfigurationError
from profile_intelligence.core.logging import get_logger
from profile_intelligence.core.types import PathLike

logger = get_logger(__name__)


class ConfigManager:
    """Load, cache, and reload split YAML configuration.

    Reads:
    - ``config/settings.yaml``
    - ``config/logging.yaml``
    - ``config/scoring.yaml``

    Example
    -------
    >>> manager = ConfigManager()
    >>> config = manager.load()
    >>> manager.settings.app.short_name
    'PIP'
    """

    _SECTIONS: frozenset[str] = frozenset(
        {
            "app",
            "paths",
            "database",
            "logging",
            "scoring",
            "importers",
            "excel",
            "ai",
            "search",
            "dashboard",
            "media",
            "nightly",
            "pipeline",
        }
    )

    def __init__(
        self,
        config_path: PathLike | None = None,
        *,
        root_dir: PathLike | None = None,
        autoload: bool = False,
    ) -> None:
        self._config_path = (
            Path(config_path).resolve() if config_path is not None else None
        )
        self._root_dir = (
            Path(root_dir).resolve() if root_dir is not None else _repo_root()
        )
        self._config: AppConfig | None = None
        if autoload:
            self.load()

    @property
    def root_dir(self) -> Path:
        """Repository / install root used for path resolution."""
        return self._root_dir

    @property
    def config_dir(self) -> Path:
        """Directory containing settings/logging/scoring YAML files."""
        return self._root_dir / "config"

    @property
    def override_path(self) -> Path | None:
        """Explicit settings override path, if configured."""
        return self._config_path

    @property
    def is_loaded(self) -> bool:
        """Whether configuration has been loaded at least once."""
        return self._config is not None

    @property
    def config(self) -> AppConfig:
        """Return the loaded config, loading it on first access."""
        if self._config is None:
            return self.load()
        return self._config

    @property
    def settings(self) -> AppConfig:
        """Alias for :attr:`config` (application settings aggregate)."""
        return self.config

    def load(self) -> AppConfig:
        """Load configuration from YAML files and cache the result."""
        config_dir = self.config_dir
        settings_path = config_dir / SETTINGS_FILENAME
        logging_path = config_dir / LOGGING_FILENAME
        scoring_path = config_dir / SCORING_FILENAME

        missing = [
            path.name
            for path in (settings_path, logging_path, scoring_path)
            if not path.exists()
        ]
        if missing:
            raise ConfigurationError(
                "Missing required configuration file(s): "
                + ", ".join(missing)
                + f" under {config_dir}"
            )

        settings_raw = _merge_file_pair(
            settings_path, config_dir / "settings.local.yaml"
        )
        logging_raw = _normalize_logging_raw(
            _merge_file_pair(logging_path, config_dir / "logging.local.yaml")
        )
        scoring_raw = _normalize_scoring_raw(
            _merge_file_pair(scoring_path, config_dir / "scoring.local.yaml")
        )

        override_path = self._config_path
        if override_path is None and os.environ.get(ENV_CONFIG_PATH):
            override_path = Path(os.environ[ENV_CONFIG_PATH]).resolve()

        if override_path is not None:
            _deep_merge(settings_raw, _load_yaml(override_path))

        _apply_env_overrides(settings_raw, logging_raw)
        self._config = _build_config(
            settings_raw,
            logging_raw,
            scoring_raw,
            config_dir=config_dir,
            config_path=override_path,
            root_dir=self._root_dir,
        )
        logger.debug(
            "Configuration loaded from %s (environment=%s)",
            config_dir,
            self._config.app.environment,
        )
        return self._config

    def reload(self) -> AppConfig:
        """Force a fresh load from disk, replacing the cached config."""
        logger.info("Reloading configuration from %s", self.config_dir)
        self._config = None
        return self.load()

    def ensure_directories(self) -> None:
        """Create runtime directories from the loaded configuration."""
        self.config.ensure_directories()

    def get(self, section: str) -> object:
        """Return a top-level config section by name."""
        if section not in self._SECTIONS:
            raise ConfigurationError(f"Unknown configuration section: {section}")
        return getattr(self.config, section)


def load_config(
    config_path: PathLike | None = None,
    *,
    root_dir: PathLike | None = None,
) -> AppConfig:
    """Load configuration via :class:`ConfigManager` (convenience wrapper)."""
    return ConfigManager(config_path, root_dir=root_dir).load()
