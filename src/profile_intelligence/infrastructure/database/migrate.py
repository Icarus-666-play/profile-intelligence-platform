"""Database migration framework and versioned schema upgrades."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence

from sqlalchemy import text
from sqlalchemy.engine import Connection

from profile_intelligence.core.exceptions import MigrationError
from profile_intelligence.core.logging import get_logger
from profile_intelligence.infrastructure.database.connection import Database

logger = get_logger(__name__)


class Migration(ABC):
    """A single, versioned schema migration."""

    version: str
    name: str

    @abstractmethod
    def up(self, connection: Connection) -> None:
        """Apply the migration."""

    def down(self, connection: Connection) -> None:
        """Optionally reverse the migration (not required for forward-only)."""
        raise NotImplementedError(
            f"Migration {self.version}_{self.name} does not support downgrade"
        )


class InitialSchemaMigration(Migration):
    """Create core tables for PIP."""

    version = "001"
    name = "initial_schema"

    def up(self, connection: Connection) -> None:
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
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    external_id VARCHAR(255),
                    display_name VARCHAR(512) NOT NULL,
                    source VARCHAR(128),
                    notes TEXT,
                    score INTEGER,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_profiles_display_name
                ON profiles (display_name)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_profiles_source
                ON profiles (source)
                """
            )
        )

    def down(self, connection: Connection) -> None:
        connection.execute(text("DROP INDEX IF EXISTS ix_profiles_source"))
        connection.execute(text("DROP INDEX IF EXISTS ix_profiles_display_name"))
        connection.execute(text("DROP TABLE IF EXISTS profiles"))


class EnrichProfilesMigration(Migration):
    """Add contact and metadata columns to profiles."""

    version = "002"
    name = "enrich_profiles"

    def up(self, connection: Connection) -> None:
        columns = {
            "email": "VARCHAR(320)",
            "phone": "VARCHAR(64)",
            "title": "VARCHAR(255)",
            "organization": "VARCHAR(255)",
            "location": "VARCHAR(255)",
            "tags": "TEXT",
            "raw_json": "TEXT",
        }
        existing = {
            row[1]
            for row in connection.execute(
                text("PRAGMA table_info(profiles)")
            ).fetchall()
        }
        for column_name, column_type in columns.items():
            if column_name in existing:
                continue
            connection.execute(
                text(
                    f"ALTER TABLE profiles ADD COLUMN {column_name} {column_type}"
                )
            )

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_profiles_email
                ON profiles (email)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_profiles_external_id
                ON profiles (external_id)
                """
            )
        )

    def down(self, connection: Connection) -> None:
        connection.execute(text("DROP INDEX IF EXISTS ix_profiles_external_id"))
        connection.execute(text("DROP INDEX IF EXISTS ix_profiles_email"))


class MediaAssetsMigration(Migration):
    """Create media_assets table for content-addressed image storage."""

    version = "003"
    name = "media_assets"

    def up(self, connection: Connection) -> None:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS media_assets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_id INTEGER,
                    content_hash VARCHAR(128) NOT NULL UNIQUE,
                    original_name VARCHAR(512),
                    content_type VARCHAR(128),
                    extension VARCHAR(32),
                    byte_size INTEGER NOT NULL DEFAULT 0,
                    width INTEGER,
                    height INTEGER,
                    storage_path VARCHAR(1024) NOT NULL,
                    thumbnail_path VARCHAR(1024),
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_media_assets_profile_id
                ON media_assets (profile_id)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_media_assets_content_hash
                ON media_assets (content_hash)
                """
            )
        )

    def down(self, connection: Connection) -> None:
        connection.execute(text("DROP INDEX IF EXISTS ix_media_assets_content_hash"))
        connection.execute(text("DROP INDEX IF EXISTS ix_media_assets_profile_id"))
        connection.execute(text("DROP TABLE IF EXISTS media_assets"))


ALL_MIGRATIONS: tuple[type[Migration], ...] = (
    InitialSchemaMigration,
    EnrichProfilesMigration,
    MediaAssetsMigration,
)


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


def run_migrations(database: Database) -> list[str]:
    """Apply all pending migrations to *database*."""
    return MigrationRunner(database).migrate()
