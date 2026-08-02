"""Top-level application orchestration service."""

from __future__ import annotations

from profile_intelligence.core.config import AppConfig
from profile_intelligence.core.logging import get_logger
from profile_intelligence.database.connection import Database
from profile_intelligence.database.migrate import run_migrations
from profile_intelligence.importers.registry import ImporterRegistry

logger = get_logger(__name__)


class ApplicationService:
    """Coordinates startup, migrations, and plugin discovery."""

    def __init__(
        self,
        config: AppConfig,
        database: Database,
        importers: ImporterRegistry,
    ) -> None:
        self.config = config
        self.database = database
        self.importers = importers
        self._started = False

    @property
    def is_started(self) -> bool:
        """Whether :meth:`start` has completed successfully."""
        return self._started

    def start(self) -> None:
        """Prepare runtime directories, migrate schema, discover plugins."""
        if self._started:
            logger.debug("Application already started")
            return

        logger.info(
            "Starting %s v%s (%s)",
            self.config.app.name,
            self.config.app.version,
            self.config.app.environment,
        )
        self.config.ensure_directories()

        if not self.database.is_connected:
            self.database.connect()

        applied = run_migrations(self.database)
        if applied:
            logger.info("Schema migrations applied: %s", ", ".join(applied))

        if self.config.importers.auto_discover:
            enabled = self.config.importers.enabled or None
            count = self.importers.discover(
                plugins_dir=self.config.plugins_dir,
                enabled=enabled,
            )
            logger.info("Discovered %d importer plugin(s)", count)

        self._started = True
        logger.info("Application ready")

    def shutdown(self) -> None:
        """Release resources."""
        logger.info("Shutting down application")
        self.database.disconnect()
        self._started = False
