"""YAML-backed application configuration.

Shipped files under ``config/``:
- ``settings.yaml`` — app, paths, database, importers, excel, ai, search, dashboard
- ``logging.yaml`` — logging options
- ``scoring.yaml`` — completeness scoring weights

Optional overlays (gitignored):
- ``settings.local.yaml``, ``logging.local.yaml``, ``scoring.local.yaml``

Additional overrides:
- ``PIP_CONFIG_PATH`` / ``--config`` merge into settings
- ``PIP_DATA_DIR``, ``PIP_LOG_LEVEL``, ``PIP_ENVIRONMENT``

Primary API: :class:`~profile_intelligence.core.config_manager.ConfigManager`.
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

SETTINGS_FILENAME = "settings.yaml"
LOGGING_FILENAME = "logging.yaml"
SCORING_FILENAME = "scoring.yaml"


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
class ScoringSection:
    """Completeness scoring configuration."""

    method: str = "completeness"
    max_score: int = 100
    weights: Mapping[str, int] = field(
        default_factory=lambda: {
            "display_name": 25,
            "email": 20,
            "phone": 10,
            "title": 10,
            "organization": 10,
            "location": 10,
            "tags": 5,
            "notes": 5,
            "external_id": 5,
        }
    )


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Fully typed application configuration."""

    app: AppSection = field(default_factory=AppSection)
    paths: PathsSection = field(default_factory=PathsSection)
    database: DatabaseSection = field(default_factory=DatabaseSection)
    logging: LoggingSection = field(default_factory=LoggingSection)
    scoring: ScoringSection = field(default_factory=ScoringSection)
    importers: ImportersSection = field(default_factory=ImportersSection)
    excel: ExcelSection = field(default_factory=ExcelSection)
    ai: AISection = field(default_factory=AISection)
    search: SearchSection = field(default_factory=SearchSection)
    dashboard: DashboardSection = field(default_factory=DashboardSection)
    config_dir: Path | None = None
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


def _load_yaml_optional(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return _load_yaml(path)


def _section(data: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    value = data.get(name, {})
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ConfigurationError(f"Configuration section '{name}' must be a mapping")
    return cast(Mapping[str, Any], value)


def _normalize_logging_raw(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Accept flat logging.yaml or nested ``logging:`` mapping."""
    if "logging" in raw and isinstance(raw.get("logging"), Mapping):
        return dict(cast(Mapping[str, Any], raw["logging"]))
    return dict(raw)


def _normalize_scoring_raw(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Accept flat scoring.yaml or nested ``scoring:`` mapping."""
    if "scoring" in raw and isinstance(raw.get("scoring"), Mapping):
        return dict(cast(Mapping[str, Any], raw["scoring"]))
    return dict(raw)


def _parse_weights(raw_weights: object, defaults: Mapping[str, int]) -> dict[str, int]:
    if raw_weights is None:
        return dict(defaults)
    if not isinstance(raw_weights, Mapping):
        raise ConfigurationError("scoring.weights must be a mapping of field -> int")
    weights: dict[str, int] = dict(defaults)
    for key, value in raw_weights.items():
        weights[str(key)] = int(value)
    return weights


def _build_config(
    settings_raw: Mapping[str, Any],
    logging_raw: Mapping[str, Any],
    scoring_raw: Mapping[str, Any],
    *,
    config_dir: Path,
    config_path: Path | None,
    root_dir: Path,
) -> AppConfig:
    # Instantiate defaults once — slotted dataclass fields are descriptors on the
    # class, so class-level attribute access cannot be used as fallback values.
    app_defaults = AppSection()
    paths_defaults = PathsSection()
    database_defaults = DatabaseSection()
    logging_defaults = LoggingSection()
    scoring_defaults = ScoringSection()
    importers_defaults = ImportersSection()
    excel_defaults = ExcelSection()
    ai_defaults = AISection()
    search_defaults = SearchSection()
    dashboard_defaults = DashboardSection()

    app_raw = _section(settings_raw, "app")
    paths_raw = _section(settings_raw, "paths")
    database_raw = _section(settings_raw, "database")
    importers_raw = _section(settings_raw, "importers")
    excel_raw = _section(settings_raw, "excel")
    ai_raw = _section(settings_raw, "ai")
    search_raw = _section(settings_raw, "search")
    dashboard_raw = _section(settings_raw, "dashboard")
    logging_data = _normalize_logging_raw(logging_raw)
    scoring_data = _normalize_scoring_raw(scoring_raw)

    enabled = importers_raw.get("enabled", [])
    if enabled is None:
        enabled_tuple: tuple[str, ...] = ()
    elif isinstance(enabled, list):
        enabled_tuple = tuple(str(item) for item in enabled)
    else:
        raise ConfigurationError("importers.enabled must be a list of strings")

    weights = _parse_weights(scoring_data.get("weights"), scoring_defaults.weights)

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
            level=str(logging_data.get("level", logging_defaults.level)).upper(),
            console=bool(logging_data.get("console", logging_defaults.console)),
            file=bool(logging_data.get("file", logging_defaults.file)),
            filename=str(logging_data.get("filename", logging_defaults.filename)),
            max_bytes=int(logging_data.get("max_bytes", logging_defaults.max_bytes)),
            backup_count=int(
                logging_data.get("backup_count", logging_defaults.backup_count)
            ),
            log_format=str(
                logging_data.get(
                    "format",
                    logging_data.get("log_format", logging_defaults.log_format),
                )
            ),
            date_format=str(
                logging_data.get("date_format", logging_defaults.date_format)
            ),
        ),
        scoring=ScoringSection(
            method=str(scoring_data.get("method", scoring_defaults.method)),
            max_score=int(scoring_data.get("max_score", scoring_defaults.max_score)),
            weights=weights,
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
        config_dir=config_dir,
        config_path=config_path,
        root_dir=root_dir,
    )


def _apply_env_overrides(
    settings_raw: MutableMapping[str, Any],
    logging_raw: MutableMapping[str, Any],
) -> None:
    """Apply supported environment variable overrides."""
    data_dir = os.environ.get(ENV_DATA_DIR)
    if data_dir:
        paths = cast(MutableMapping[str, Any], settings_raw.setdefault("paths", {}))
        paths["data_dir"] = data_dir
        db_file = paths.get("database_file", "data/pip.sqlite3")
        if not Path(str(db_file)).is_absolute():
            paths["database_file"] = str(Path(data_dir) / "pip.sqlite3")

    log_level = os.environ.get(ENV_LOG_LEVEL)
    if log_level:
        logging_raw["level"] = log_level.upper()

    environment = os.environ.get(ENV_ENVIRONMENT)
    if environment:
        app_section = cast(
            MutableMapping[str, Any], settings_raw.setdefault("app", {})
        )
        app_section["environment"] = environment


def _merge_file_pair(base_path: Path, local_path: Path) -> dict[str, Any]:
    merged = _load_yaml(base_path)
    local = _load_yaml_optional(local_path)
    if local:
        _deep_merge(merged, local)
    return merged


def __getattr__(name: str) -> object:
    """Lazy re-export of ConfigManager/load_config to avoid circular imports."""
    if name in {"ConfigManager", "load_config"}:
        from profile_intelligence.core import config_manager

        return getattr(config_manager, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ENV_CONFIG_PATH",
    "ENV_DATA_DIR",
    "ENV_ENVIRONMENT",
    "ENV_LOG_LEVEL",
    "LOGGING_FILENAME",
    "SCORING_FILENAME",
    "SETTINGS_FILENAME",
    "AISection",
    "AppConfig",
    "AppSection",
    "DashboardSection",
    "DatabaseSection",
    "ExcelSection",
    "ImportersSection",
    "LoggingSection",
    "PathsSection",
    "ScoringSection",
    "SearchSection",
]
