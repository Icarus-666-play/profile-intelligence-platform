"""Safe Settings snapshot for the React Settings page."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit, urlunsplit

from profile_intelligence.core.config import AppConfig


def settings_to_dict(config: AppConfig) -> dict[str, Any]:
    """Serialize a redacted configuration snapshot for Settings UI."""
    playwright_available = _playwright_available()
    return {
        "theme": {
            "options": ["default", "harbor", "forest"],
            "note": "Theme is stored in the browser (localStorage).",
            "source": "client",
        },
        "database": {
            "driver": config.database.driver,
            "path": str(config.database_path),
            "url": _redact_url(config.database.url),
            "echo_sql": config.database.echo_sql,
            "timeout_seconds": config.database.timeout_seconds,
            "foreign_keys": config.database.foreign_keys,
            "check_same_thread": config.database.check_same_thread,
            "exists": config.database_path.is_file(),
        },
        "plugins": {
            "directory": str(config.plugins_dir),
            "auto_discover": config.importers.auto_discover,
            "enabled": list(config.importers.enabled),
            "note": "Empty enabled list means all discovered plugins.",
        },
        "scoring": {
            "method": config.scoring.method,
            "max_score": config.scoring.max_score,
            "weights": dict(config.scoring.weights),
            "daily_rescore": config.daily.rescore,
            "config_file": "config/scoring.yaml",
        },
        "import_folder": {
            "path": str(config.daily_import_dir),
            "configured": config.daily.import_dir,
            "recursive": config.daily.recursive,
            "excel_path": str(config.resolve_path(config.daily.excel_path)),
            "dashboard_path": str(
                config.resolve_path(config.daily.dashboard_path)
            ),
            "exists": config.daily_import_dir.is_dir(),
        },
        "playwright": {
            "available": playwright_available,
            "enabled": False,
            "status": "available" if playwright_available else "not_installed",
            "note": (
                "Optional browser automation is not wired into the import "
                "pipeline yet. Install the Playwright Python package to prepare."
            ),
        },
        "backups": {
            "directory": str(config.exports_dir / "backups"),
            "log_backup_count": config.logging.backup_count,
            "note": "Create timestamped copies of the SQLite database.",
        },
        "meta": {
            "app": config.app.name,
            "version": config.app.version,
            "environment": config.app.environment,
            "config_dir": str(config.config_dir) if config.config_dir else None,
            "root_dir": str(config.root_dir),
        },
    }


def _redact_url(url: str | None) -> str | None:
    if not url:
        return None
    parts = urlsplit(url)
    if not parts.username and not parts.password:
        return url
    host = parts.hostname or ""
    if parts.port:
        host = f"{host}:{parts.port}"
    user = parts.username or ""
    auth = f"{user}:***@" if user or parts.password else ""
    netloc = f"{auth}{host}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def _playwright_available() -> bool:
    try:
        import importlib.util

        return importlib.util.find_spec("playwright") is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


__all__ = ["settings_to_dict"]
