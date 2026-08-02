"""YAML-backed application configuration.

Load order:
1. ``config/default.yaml`` (shipped defaults)
2. Optional override file (``config/local.yaml`` or ``PIP_CONFIG_PATH``)
3. Environment variable overrides for select keys
"""

from __future__ import annotations

import os
from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import yaml

from profile_intelligence.core.exceptions import ConfigurationError
from profile_intelligence.core.types import PathLike

ENV_CONFIG_PATH = "PIP_CONFIG_PATH"
ENV_DATA_DIR = "PIP_DATA_DIR"
ENV_LOG_LEVEL = "PIP_LOG_LEVEL"
ENV_ENVIRONMENT = "PIP_ENVIRONMENT"


def _repo_root() -> Path:
    """Return the repository root (two levels above this package file's parents)."""
    # src/profile_intelligence/core/config.py -> repo root
    return Path(__file__).resolve().parents[3]


def _deep_merge(
    base: MutableMapping[str, Any],
    override: Mapping[str, Any],
) -> MutableMapping[str, Any]:
    """Recursively merge *override* into *base* (mutates and returns *base*)."""
    for key, value in override.items():
        if (
            key in base
            and isinstance(base[key], MutableMapping)
            and isinstance(value, Mapping)
        ):
            _deep_merge(cast(MutableMapping[str, Any], base[key]), value)
        else:
            base[key] = value
    return base


@dataclass(frozen=True, slots=True)
class AppSection:
    """Top-level application metadata."""

    name: str = "Profile Intelligence Platform"
    short_name: str = "PIP"
    version: str = "0.1.0"
    environment: str = "development"


@dataclass(frozen=True, slots=True)
class PathsSection:
    """Filesystem path configuration."""

    data_dir: str = "data"
    database_file: str = "data/pip.sqlite3"
    logs_dir: str = "logs"
    exports_dir: str = "exports"
    plugins_dir: str = "plugins"


@dataclass(frozen=True, slots=True)
class DatabaseSection:
    """SQLite / SQLAlchemy connection settings."""

    echo_sql: bool = False
    timeout_seconds: float = 30.0
    check_same_thread: bool = False
    foreign_keys: bool = True


@dataclass(frozen=True, slots=True)
class LoggingSection:
    """Logging configuration."""

    level: str = "INFO"
    console: bool = True
    file: bool = True
    filename: str = "pip.log"
    max_bytes: int = 10_485_760
    backup_count: int = 5
    log_format: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"


@dataclass(frozen=True, slots=True)
class ImportersSection:
    """Importer plugin settings."""

    auto_discover: bool = True
    enabled: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class ExcelSection:
    """Excel reporting defaults."""

    default_sheet_name: str = "Profiles"
    date_format: str = "YYYY-MM-DD"


@dataclass(frozen=True, slots=True)
class AISection:
    """AI integration settings (disabled by default)."""

    enabled: bool = False
    provider: str | None = None
    model: str | None = None


@dataclass(frozen=True, slots=True)
class SearchSection:
    """Search defaults."""

    default_limit: int = 50
    fuzzy: bool = True


@dataclass(frozen=True, slots=True)
class DashboardSection:
    """Dashboard refresh settings."""

    refresh_seconds: int = 30


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Fully typed application configuration."""

    app: AppSection = field(default_factory=AppSection)
    paths: PathsSection = field(default_factory=PathsSection)
    database: DatabaseSection = field(default_factory=DatabaseSection)
    logging: LoggingSection = field(default_factory=LoggingSection)
    importers: ImportersSection = field(default_factory=ImportersSection)
    excel: ExcelSection = field(default_factory=ExcelSection)
    ai: AISection = field(default_factory=AISection)
    search: SearchSection = field(default_factory=SearchSection)
    dashboard: DashboardSection = field(default_factory=DashboardSection)
    config_path: Path | None = None
    root_dir: Path = field(default_factory=_repo_root)

    def resolve_path(self, relative: PathLike) -> Path:
        """Resolve a configured path relative to :attr:`root_dir` when needed."""
        path = Path(relative)
        if path.is_absolute():
            return path
        return (self.root_dir / path).resolve()

    @property
    def data_dir(self) -> Path:
        """Absolute path to the application data directory."""
        return self.resolve_path(self.paths.data_dir)

    @property
    def database_path(self) -> Path:
        """Absolute path to the SQLite database file."""
        return self.resolve_path(self.paths.database_file)

    @property
    def logs_dir(self) -> Path:
        """Absolute path to the logs directory."""
        return self.resolve_path(self.paths.logs_dir)

    @property
    def exports_dir(self) -> Path:
        """Absolute path to the exports directory."""
        return self.resolve_path(self.paths.exports_dir)

    @property
    def plugins_dir(self) -> Path:
        """Absolute path to the external plugins directory."""
        return self.resolve_path(self.paths.plugins_dir)

    def ensure_directories(self) -> None:
        """Create runtime directories if they do not exist."""
        for directory in (
            self.data_dir,
            self.logs_dir,
            self.exports_dir,
            self.plugins_dir,
            self.database_path.parent,
        ):
            directory.mkdir(parents=True, exist_ok=True)


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigurationError(f"Configuration file not found: {path}")
    try:
        with path.open(encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
    except yaml.YAMLError as exc:
        raise ConfigurationError(
            f"Invalid YAML in configuration file: {path}",
            cause=exc,
        ) from exc
    except OSError as exc:
        raise ConfigurationError(
            f"Unable to read configuration file: {path}",
            cause=exc,
        ) from exc
    if not isinstance(data, dict):
        raise ConfigurationError(
            f"Configuration root must be a mapping, got {type(data).__name__}"
        )
    return cast(dict[str, Any], data)


def _section(data: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    value = data.get(name, {})
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ConfigurationError(f"Configuration section '{name}' must be a mapping")
    return cast(Mapping[str, Any], value)


def _build_config(
    raw: Mapping[str, Any],
    *,
    config_path: Path | None,
    root_dir: Path,
) -> AppConfig:
    # Instantiate defaults once — slotted dataclass fields are descriptors on the
    # class, so class-level attribute access cannot be used as fallback values.
    app_defaults = AppSection()
    paths_defaults = PathsSection()
    database_defaults = DatabaseSection()
    logging_defaults = LoggingSection()
    importers_defaults = ImportersSection()
    excel_defaults = ExcelSection()
    ai_defaults = AISection()
    search_defaults = SearchSection()
    dashboard_defaults = DashboardSection()

    app_raw = _section(raw, "app")
    paths_raw = _section(raw, "paths")
    database_raw = _section(raw, "database")
    logging_raw = _section(raw, "logging")
    importers_raw = _section(raw, "importers")
    excel_raw = _section(raw, "excel")
    ai_raw = _section(raw, "ai")
    search_raw = _section(raw, "search")
    dashboard_raw = _section(raw, "dashboard")

    enabled = importers_raw.get("enabled", [])
    if enabled is None:
        enabled_tuple: tuple[str, ...] = ()
    elif isinstance(enabled, list):
        enabled_tuple = tuple(str(item) for item in enabled)
    else:
        raise ConfigurationError("importers.enabled must be a list of strings")

    return AppConfig(
        app=AppSection(
            name=str(app_raw.get("name", app_defaults.name)),
            short_name=str(app_raw.get("short_name", app_defaults.short_name)),
            version=str(app_raw.get("version", app_defaults.version)),
            environment=str(app_raw.get("environment", app_defaults.environment)),
        ),
        paths=PathsSection(
            data_dir=str(paths_raw.get("data_dir", paths_defaults.data_dir)),
            database_file=str(
                paths_raw.get("database_file", paths_defaults.database_file)
            ),
            logs_dir=str(paths_raw.get("logs_dir", paths_defaults.logs_dir)),
            exports_dir=str(paths_raw.get("exports_dir", paths_defaults.exports_dir)),
            plugins_dir=str(paths_raw.get("plugins_dir", paths_defaults.plugins_dir)),
        ),
        database=DatabaseSection(
            echo_sql=bool(database_raw.get("echo_sql", database_defaults.echo_sql)),
            timeout_seconds=float(
                database_raw.get(
                    "timeout_seconds", database_defaults.timeout_seconds
                )
            ),
            check_same_thread=bool(
                database_raw.get(
                    "check_same_thread", database_defaults.check_same_thread
                )
            ),
            foreign_keys=bool(
                database_raw.get("foreign_keys", database_defaults.foreign_keys)
            ),
        ),
        logging=LoggingSection(
            level=str(logging_raw.get("level", logging_defaults.level)).upper(),
            console=bool(logging_raw.get("console", logging_defaults.console)),
            file=bool(logging_raw.get("file", logging_defaults.file)),
            filename=str(logging_raw.get("filename", logging_defaults.filename)),
            max_bytes=int(logging_raw.get("max_bytes", logging_defaults.max_bytes)),
            backup_count=int(
                logging_raw.get("backup_count", logging_defaults.backup_count)
            ),
            log_format=str(
                logging_raw.get(
                    "format",
                    logging_raw.get("log_format", logging_defaults.log_format),
                )
            ),
            date_format=str(
                logging_raw.get("date_format", logging_defaults.date_format)
            ),
        ),
        importers=ImportersSection(
            auto_discover=bool(
                importers_raw.get(
                    "auto_discover", importers_defaults.auto_discover
                )
            ),
            enabled=enabled_tuple,
        ),
        excel=ExcelSection(
            default_sheet_name=str(
                excel_raw.get(
                    "default_sheet_name", excel_defaults.default_sheet_name
                )
            ),
            date_format=str(
                excel_raw.get("date_format", excel_defaults.date_format)
            ),
        ),
        ai=AISection(
            enabled=bool(ai_raw.get("enabled", ai_defaults.enabled)),
            provider=ai_raw.get("provider", ai_defaults.provider),
            model=ai_raw.get("model", ai_defaults.model),
        ),
        search=SearchSection(
            default_limit=int(
                search_raw.get("default_limit", search_defaults.default_limit)
            ),
            fuzzy=bool(search_raw.get("fuzzy", search_defaults.fuzzy)),
        ),
        dashboard=DashboardSection(
            refresh_seconds=int(
                dashboard_raw.get(
                    "refresh_seconds", dashboard_defaults.refresh_seconds
                )
            ),
        ),
        config_path=config_path,
        root_dir=root_dir,
    )


def _apply_env_overrides(raw: MutableMapping[str, Any]) -> None:
    """Apply supported environment variable overrides onto raw config."""
    data_dir = os.environ.get(ENV_DATA_DIR)
    if data_dir:
        paths = cast(MutableMapping[str, Any], raw.setdefault("paths", {}))
        paths["data_dir"] = data_dir
        # Keep database under the overridden data directory unless absolute.
        db_file = paths.get("database_file", "data/pip.sqlite3")
        if not Path(str(db_file)).is_absolute():
            paths["database_file"] = str(Path(data_dir) / "pip.sqlite3")

    log_level = os.environ.get(ENV_LOG_LEVEL)
    if log_level:
        logging_section = cast(
            MutableMapping[str, Any], raw.setdefault("logging", {})
        )
        logging_section["level"] = log_level.upper()

    environment = os.environ.get(ENV_ENVIRONMENT)
    if environment:
        app_section = cast(MutableMapping[str, Any], raw.setdefault("app", {}))
        app_section["environment"] = environment


def load_config(
    config_path: PathLike | None = None,
    *,
    root_dir: PathLike | None = None,
) -> AppConfig:
    """Load and validate application configuration.

    Parameters
    ----------
    config_path:
        Optional override YAML path. Defaults to ``PIP_CONFIG_PATH``, then
        ``<root>/config/local.yaml`` if present, otherwise only defaults.
    root_dir:
        Repository / install root used to resolve relative paths.
    """
    root = Path(root_dir).resolve() if root_dir is not None else _repo_root()
    default_path = root / "config" / "default.yaml"

    if not default_path.exists():
        raise ConfigurationError(
            f"Default configuration missing: {default_path}. "
            "Ensure the repository config/ directory is present."
        )

    merged: dict[str, Any] = _load_yaml(default_path)

    override_path: Path | None = None
    if config_path is not None:
        override_path = Path(config_path).resolve()
    elif os.environ.get(ENV_CONFIG_PATH):
        override_path = Path(os.environ[ENV_CONFIG_PATH]).resolve()
    else:
        local_path = root / "config" / "local.yaml"
        if local_path.exists():
            override_path = local_path

    if override_path is not None:
        _deep_merge(merged, _load_yaml(override_path))

    _apply_env_overrides(merged)
    return _build_config(merged, config_path=override_path, root_dir=root)
