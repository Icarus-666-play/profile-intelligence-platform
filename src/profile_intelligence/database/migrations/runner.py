"""Migration discovery and execution."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from sqlalchemy import text

from profile_intelligence.core.exceptions import MigrationError
from profile_intelligence.core.logging import get_logger
from profile_intelligence.database.connection import Database
from profile_intelligence.database.migrations.base import Migration
from profile_intelligence.database.migrations.versions import ALL_MIGRATIONS

logger = get_logger(__name__)


class MigrationRunner:
    """Applies pending migrations in version order."""

    def __init__(
        self,
        database: Database,
        migrations: Iterable[type[Migration]] | None = None,
    ) -> None:
        self._database = database
        self._migration_types: tuple[type[Migration], ...] = tuple(
            migrations if migrations is not None else ALL_MIGRATIONS
        )

    def available(self) -> Sequence[Migration]:
        """Instantiate and return all known migrations, sorted by version."""
        instances = [cls() for cls in self._migration_types]
        return sorted(instances, key=lambda migration: migration.version)

    def applied_versions(self) -> set[str]:
        """Return versions already recorded in ``schema_migrations``."""
        self._ensure_migrations_table()
        with self._database.engine.connect() as connection:
            rows = connection.execute(
                text("SELECT version FROM schema_migrations")
            ).fetchall()
        return {str(row[0]) for row in rows}

    def pending(self) -> Sequence[Migration]:
        """Return migrations that have not yet been applied."""
        applied = self.applied_versions()
        return [m for m in self.available() if m.version not in applied]

    def migrate(self) -> list[str]:
        """Apply all pending migrations. Returns applied version strings."""
        pending = self.pending()
        if not pending:
            logger.info("Database schema is up to date")
            return []

        applied: list[str] = []
        for migration in pending:
            self._apply(migration)
            applied.append(migration.version)
        logger.info("Applied %d migration(s): %s", len(applied), ", ".join(applied))
        return applied

    def _apply(self, migration: Migration) -> None:
        logger.info("Applying migration %s_%s", migration.version, migration.name)
        try:
            with self._database.engine.begin() as connection:
                migration.up(connection)
                connection.execute(
                    text(
                        """
                        INSERT INTO schema_migrations (version, name)
                        VALUES (:version, :name)
                        """
                    ),
                    {"version": migration.version, "name": migration.name},
                )
        except Exception as exc:
            raise MigrationError(
                f"Failed to apply migration {migration.version}_{migration.name}",
                cause=exc,
            ) from exc

    def _ensure_migrations_table(self) -> None:
        try:
            with self._database.engine.begin() as connection:
                connection.execute(
                    text(
                        """
                        CREATE TABLE IF NOT EXISTS schema_migrations (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            version VARCHAR(64) NOT NULL UNIQUE,
                            name VARCHAR(255) NOT NULL,
                            applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                        )
                        """
                    )
                )
        except Exception as exc:
            raise MigrationError(
                "Unable to ensure schema_migrations table exists",
                cause=exc,
            ) from exc
