"""Centralized logging configuration.

File outputs under ``logs/``:
- ``application.log`` — general application activity
- ``import.log`` — importer / import-pipeline activity
- ``errors.log`` — ERROR and above from all loggers
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from typing import Final

from profile_intelligence.core.config import AppConfig, LoggingSection

_CONFIGURED: bool = False
_ROOT_LOGGER_NAME: Final[str] = "profile_intelligence"
_IMPORT_LOGGER_PREFIXES: Final[tuple[str, ...]] = (
    "profile_intelligence.infrastructure.importers",
    "profile_intelligence.importers",  # compatibility shim path
    "profile_intelligence.application.use_cases.import_pipeline",
    "profile_intelligence.application.use_cases.import_service",
    "profile_intelligence.application.use_cases.parse_document",
    "profile_intelligence.application.use_cases.normalize_profiles",
    "profile_intelligence.application.use_cases.validate_profiles",
)


class _ImportLogFilter(logging.Filter):
    """Allow only importer / import-pipeline log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        name = record.name
        for prefix in _IMPORT_LOGGER_PREFIXES:
            if name == prefix or name.startswith(f"{prefix}."):
                return True
        return False


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a logger under the PIP namespace.

    Pass a module ``__name__`` or a short component name. Names that already
    start with ``profile_intelligence`` are used as-is.
    """
    if name is None:
        return logging.getLogger(_ROOT_LOGGER_NAME)
    if name == _ROOT_LOGGER_NAME or name.startswith(f"{_ROOT_LOGGER_NAME}."):
        return logging.getLogger(name)
    return logging.getLogger(f"{_ROOT_LOGGER_NAME}.{name}")


def configure_logging(
    config: AppConfig | LoggingSection,
    *,
    force: bool = False,
) -> None:
    """Configure application logging from settings.

    Safe to call multiple times; subsequent calls are no-ops unless
    ``force=True``.

    When file logging is enabled, writes:
    - ``logs/application.log``
    - ``logs/import.log``
    - ``logs/errors.log``
    """
    global _CONFIGURED
    if _CONFIGURED and not force:
        return

    if isinstance(config, AppConfig):
        section = config.logging
        logs_dir = config.logs_dir
        config.ensure_directories()
    else:
        section = config
        logs_dir = None

    level = getattr(logging, section.level.upper(), logging.INFO)
    root = logging.getLogger(_ROOT_LOGGER_NAME)
    _close_handlers(root)
    root.setLevel(level)
    root.propagate = False

    formatter = logging.Formatter(
        fmt=section.log_format,
        datefmt=section.date_format,
    )

    if section.console:
        console_handler = logging.StreamHandler(stream=sys.stderr)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root.addHandler(console_handler)

    if section.file:
        if logs_dir is None:
            raise ValueError(
                "File logging requires AppConfig (to resolve logs_dir), "
                "not LoggingSection alone."
            )

        application_handler = _rotating_handler(
            logs_dir / section.application_filename,
            section=section,
            level=level,
            formatter=formatter,
        )
        root.addHandler(application_handler)

        import_handler = _rotating_handler(
            logs_dir / section.import_filename,
            section=section,
            level=level,
            formatter=formatter,
        )
        import_handler.addFilter(_ImportLogFilter())
        root.addHandler(import_handler)

        errors_handler = _rotating_handler(
            logs_dir / section.errors_filename,
            section=section,
            level=logging.ERROR,
            formatter=formatter,
        )
        root.addHandler(errors_handler)

    _CONFIGURED = True
    get_logger(__name__).debug(
        "Logging configured (level=%s, console=%s, file=%s, files=%s/%s/%s)",
        section.level,
        section.console,
        section.file,
        section.application_filename,
        section.import_filename,
        section.errors_filename,
    )


def reset_logging() -> None:
    """Reset logging state (intended for tests)."""
    global _CONFIGURED
    root = logging.getLogger(_ROOT_LOGGER_NAME)
    _close_handlers(root)
    _CONFIGURED = False


def _rotating_handler(
    path: object,
    *,
    section: LoggingSection,
    level: int,
    formatter: logging.Formatter,
) -> RotatingFileHandler:
    handler = RotatingFileHandler(
        filename=str(path),
        maxBytes=section.max_bytes,
        backupCount=section.backup_count,
        encoding="utf-8",
    )
    handler.setLevel(level)
    handler.setFormatter(formatter)
    return handler


def _close_handlers(logger: logging.Logger) -> None:
    """Close and detach all handlers on *logger*."""
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
