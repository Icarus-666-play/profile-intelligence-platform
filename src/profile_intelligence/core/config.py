"""YAML-backed application configuration.

Shipped files under ``config/``:
- ``settings.yaml`` — app, paths, database, importers, excel, ai, search,
  dashboard, media, nightly, pipeline
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
    """SQLAlchemy connection settings (SQLite or PostgreSQL)."""

    driver: str = "sqlite"
    url: str | None = None
    echo_sql: bool = False
    timeout_seconds: float = 30.0
    check_same_thread: bool = False
    foreign_keys: bool = True


@dataclass(frozen=True, slots=True)
class LoggingSection:
    """Logging configuration.

    File outputs are written under ``logs/``:
    - ``application.log`` — general application activity
    - ``import.log`` — importer / import-pipeline activity
    - ``errors.log`` — ERROR and above from all loggers
    """

    level: str = "INFO"
    console: bool = True
    file: bool = True
    application_filename: str = "application.log"
    import_filename: str = "import.log"
    errors_filename: str = "errors.log"
    max_bytes: int = 10_485_760
    backup_count: int = 5
    log_format: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"

    @property
    def filename(self) -> str:
        """Backward-compatible alias for :attr:`application_filename`."""
        return self.application_filename


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
class MediaSection:
    """Local media / image storage settings.

    Image pipeline::

        Image → Download → Hash → Duplicate Detection → Thumbnail → Storage
    """

    root_dir: str = "data/media"
    thumbnails_dir: str = "data/media/thumbnails"
    downloads_dir: str = "data/media/downloads"
    hash_algorithm: str = "sha256"
    thumbnail_max_size: int = 256
    thumbnail_format: str = "JPEG"
    thumbnail_quality: int = 85
    allow_remote_download: bool = True
    download_timeout_seconds: float = 30.0


@dataclass(frozen=True, slots=True)
class CacheSection:
    """Application cache settings.

    Backends::

        cache/
          SQLite
          Memory
          File
          Redis (future)
    """

    backend: str = "memory"
    ttl_seconds: float | None = 3600.0
    file_dir: str = "data/cache"
    sqlite_file: str = "data/cache.sqlite3"
    redis_url: str | None = None


@dataclass(frozen=True, slots=True)
class NightlySection:
    """Nightly automation workflow settings.

    Flow::

        Import every night
         ↓
        Update database
         ↓
        Recalculate scores
         ↓
        Generate Excel report
         ↓
        Export dashboard
    """

    import_dir: str = "data/inbox"
    excel_path: str = "exports/nightly-profiles.xlsx"
    dashboard_path: str = "exports/nightly-dashboard.txt"
    rescore: bool = True
    recursive: bool = False


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


DEFAULT_PIPELINE_STAGES: tuple[str, ...] = (
    "parser",
    "normalizer",
    "validator",
    "duplicate_detector",
    "scorer",
    "repository",
)


@dataclass(frozen=True, slots=True)
class PipelineSection:
    """Ordered import processing stages after RawDocument load.

    YAML list form::

        pipeline:
          - parser
          - normalizer
          - validator
          - duplicate_detector
          - scorer
          - repository

    Or mapping form::

        pipeline:
          stages:
            - parser
            - normalizer
            ...
    """

    stages: tuple[str, ...] = DEFAULT_PIPELINE_STAGES


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
    media: MediaSection = field(default_factory=MediaSection)
    cache: CacheSection = field(default_factory=CacheSection)
    nightly: NightlySection = field(default_factory=NightlySection)
    pipeline: PipelineSection = field(default_factory=PipelineSection)
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

    @property
    def media_dir(self) -> Path:
        """Absolute path to the media storage directory."""
        return self.resolve_path(self.media.root_dir)

    @property
    def thumbnails_dir(self) -> Path:
        """Absolute path to the thumbnail storage directory."""
        return self.resolve_path(self.media.thumbnails_dir)

    @property
    def media_downloads_dir(self) -> Path:
        """Absolute path to the image download staging directory."""
        return self.resolve_path(self.media.downloads_dir)

    @property
    def cache_dir(self) -> Path:
        """Absolute path to the file-cache directory."""
        return self.resolve_path(self.cache.file_dir)

    @property
    def cache_sqlite_path(self) -> Path:
        """Absolute path to the SQLite cache database file."""
        return self.resolve_path(self.cache.sqlite_file)

    @property
    def nightly_import_dir(self) -> Path:
        """Absolute path to the nightly import inbox."""
        return self.resolve_path(self.nightly.import_dir)

    @property
    def nightly_excel_path(self) -> Path:
        """Absolute path for the nightly Excel report."""
        return self.resolve_path(self.nightly.excel_path)

    @property
    def nightly_dashboard_path(self) -> Path:
        """Absolute path for the nightly dashboard export."""
        return self.resolve_path(self.nightly.dashboard_path)

    def ensure_directories(self) -> None:
        """Create runtime directories if they do not exist."""
        for directory in (
            self.data_dir,
            self.logs_dir,
            self.exports_dir,
            self.plugins_dir,
            self.media_dir,
            self.thumbnails_dir,
            self.media_downloads_dir,
            self.cache_dir,
            self.cache_sqlite_path.parent,
            self.nightly_import_dir,
            self.database_path.parent,
            self.nightly_excel_path.parent,
            self.nightly_dashboard_path.parent,
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


def _parse_pipeline(raw: object) -> PipelineSection:
    """Parse ``pipeline`` as a stage list or ``{stages: [...]}`` mapping."""
    if raw is None:
        return PipelineSection()
    if isinstance(raw, list):
        stages = tuple(str(item) for item in raw)
        return PipelineSection(stages=stages or DEFAULT_PIPELINE_STAGES)
    if isinstance(raw, Mapping):
        stages_raw = raw.get("stages", DEFAULT_PIPELINE_STAGES)
        if stages_raw is None:
            return PipelineSection()
        if not isinstance(stages_raw, list):
            raise ConfigurationError("pipeline.stages must be a list of strings")
        stages = tuple(str(item) for item in stages_raw)
        return PipelineSection(stages=stages or DEFAULT_PIPELINE_STAGES)
    raise ConfigurationError(
        "pipeline must be a list of stages or a mapping with 'stages'"
    )


def _normalize_logging_raw(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Accept flat logging.yaml or nested ``logging:`` mapping."""
    if "logging" in raw and isinstance(raw.get("logging"), Mapping):
        return dict(cast(Mapping[str, Any], raw["logging"]))
    return dict(raw)


def _resolve_log_filename(
    logging_data: Mapping[str, Any],
    *,
    key: str,
    default: str,
    legacy_key: str | None = None,
) -> str:
    """Resolve a log filename from ``files.<key>`` or a legacy flat key."""
    files_raw = logging_data.get("files")
    if isinstance(files_raw, Mapping) and files_raw.get(key):
        return str(files_raw[key])
    if legacy_key is not None and logging_data.get(legacy_key):
        return str(logging_data[legacy_key])
    flat_key = f"{key}_filename"
    if logging_data.get(flat_key):
        return str(logging_data[flat_key])
    return default


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


def _optional_str(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_float(value: object | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float, str)):
        return float(value)
    raise ConfigurationError(
        f"Expected a numeric value, got {type(value).__name__}"
    )


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
    media_defaults = MediaSection()
    cache_defaults = CacheSection()
    nightly_defaults = NightlySection()

    app_raw = _section(settings_raw, "app")
    paths_raw = _section(settings_raw, "paths")
    database_raw = _section(settings_raw, "database")
    importers_raw = _section(settings_raw, "importers")
    excel_raw = _section(settings_raw, "excel")
    ai_raw = _section(settings_raw, "ai")
    search_raw = _section(settings_raw, "search")
    dashboard_raw = _section(settings_raw, "dashboard")
    media_raw = _section(settings_raw, "media")
    cache_raw = _section(settings_raw, "cache")
    nightly_raw = _section(settings_raw, "nightly")
    pipeline_section = _parse_pipeline(settings_raw.get("pipeline"))
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
            driver=str(database_raw.get("driver", database_defaults.driver)),
            url=_optional_str(database_raw.get("url", database_defaults.url)),
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
            application_filename=_resolve_log_filename(
                logging_data,
                key="application",
                legacy_key="filename",
                default=logging_defaults.application_filename,
            ),
            import_filename=_resolve_log_filename(
                logging_data,
                key="import",
                default=logging_defaults.import_filename,
            ),
            errors_filename=_resolve_log_filename(
                logging_data,
                key="errors",
                default=logging_defaults.errors_filename,
            ),
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
        media=MediaSection(
            root_dir=str(media_raw.get("root_dir", media_defaults.root_dir)),
            thumbnails_dir=str(
                media_raw.get("thumbnails_dir", media_defaults.thumbnails_dir)
            ),
            downloads_dir=str(
                media_raw.get("downloads_dir", media_defaults.downloads_dir)
            ),
            hash_algorithm=str(
                media_raw.get("hash_algorithm", media_defaults.hash_algorithm)
            ).lower(),
            thumbnail_max_size=int(
                media_raw.get(
                    "thumbnail_max_size", media_defaults.thumbnail_max_size
                )
            ),
            thumbnail_format=str(
                media_raw.get(
                    "thumbnail_format", media_defaults.thumbnail_format
                )
            ).upper(),
            thumbnail_quality=int(
                media_raw.get(
                    "thumbnail_quality", media_defaults.thumbnail_quality
                )
            ),
            allow_remote_download=bool(
                media_raw.get(
                    "allow_remote_download",
                    media_defaults.allow_remote_download,
                )
            ),
            download_timeout_seconds=float(
                media_raw.get(
                    "download_timeout_seconds",
                    media_defaults.download_timeout_seconds,
                )
            ),
        ),
        cache=CacheSection(
            backend=str(cache_raw.get("backend", cache_defaults.backend)).lower(),
            ttl_seconds=_optional_float(
                cache_raw.get("ttl_seconds", cache_defaults.ttl_seconds)
            ),
            file_dir=str(cache_raw.get("file_dir", cache_defaults.file_dir)),
            sqlite_file=str(
                cache_raw.get("sqlite_file", cache_defaults.sqlite_file)
            ),
            redis_url=_optional_str(
                cache_raw.get("redis_url", cache_defaults.redis_url)
            ),
        ),
        nightly=NightlySection(
            import_dir=str(
                nightly_raw.get("import_dir", nightly_defaults.import_dir)
            ),
            excel_path=str(
                nightly_raw.get("excel_path", nightly_defaults.excel_path)
            ),
            dashboard_path=str(
                nightly_raw.get(
                    "dashboard_path", nightly_defaults.dashboard_path
                )
            ),
            rescore=bool(nightly_raw.get("rescore", nightly_defaults.rescore)),
            recursive=bool(
                nightly_raw.get("recursive", nightly_defaults.recursive)
            ),
        ),
        pipeline=pipeline_section,
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
    "DEFAULT_PIPELINE_STAGES",
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
    "CacheSection",
    "DashboardSection",
    "DatabaseSection",
    "ExcelSection",
    "ImportersSection",
    "LoggingSection",
    "MediaSection",
    "NightlySection",
    "PathsSection",
    "PipelineSection",
    "ScoringSection",
    "SearchSection",
]
