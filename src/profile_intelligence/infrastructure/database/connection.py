"""Database connection management via SQLAlchemy."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from profile_intelligence.core.config import AppConfig, DatabaseSection
from profile_intelligence.core.exceptions import ConfigurationError, DatabaseError
from profile_intelligence.core.logging import get_logger
from profile_intelligence.core.types import PathLike

logger = get_logger(__name__)

_SQLITE_DRIVERS = frozenset({"sqlite", "sqlite3"})
_POSTGRES_DRIVERS = frozenset({"postgresql", "postgres", "pgsql"})


class Database:
    """Owns the SQLAlchemy engine and session factory for PIP."""

    def __init__(
        self,
        database_path: PathLike | None = None,
        settings: DatabaseSection | None = None,
        *,
        url: str | None = None,
    ) -> None:
        self.settings = settings or DatabaseSection()
        self.path = Path(database_path) if database_path is not None else None
        self.url = (url or self.settings.url or "").strip() or None
        self.driver = self.settings.driver.strip().lower() or "sqlite"
        self._engine: Engine | None = None
        self._session_factory: sessionmaker[Session] | None = None

    @property
    def engine(self) -> Engine:
        """Lazy-initialized SQLAlchemy engine."""
        if self._engine is None:
            raise DatabaseError("Database is not connected. Call connect() first.")
        return self._engine

    @property
    def is_connected(self) -> bool:
        """Return whether the engine has been created."""
        return self._engine is not None

    def connect(self) -> None:
        """Create the engine for the configured driver."""
        if self._engine is not None:
            return

        try:
            engine_url, connect_args = self._build_engine_args()
            self._engine = create_engine(
                engine_url,
                echo=self.settings.echo_sql,
                connect_args=connect_args,
                pool_pre_ping=self.driver in _POSTGRES_DRIVERS,
                future=True,
            )
            if self.driver in _SQLITE_DRIVERS and self.settings.foreign_keys:
                event.listen(self._engine, "connect", _set_sqlite_pragma)

            self._session_factory = sessionmaker(
                bind=self._engine,
                autoflush=False,
                autocommit=False,
                expire_on_commit=False,
                future=True,
            )
            with self._engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            logger.info(
                "Connected to %s database (%s)",
                self.driver,
                self.path or self.url or engine_url,
            )
        except (DatabaseError, ConfigurationError):
            raise
        except Exception as exc:
            self._engine = None
            self._session_factory = None
            target = self.path or self.url or self.driver
            raise DatabaseError(
                f"Failed to connect to database: {target}",
                cause=exc,
            ) from exc

    def disconnect(self) -> None:
        """Dispose the engine and clear the session factory."""
        if self._engine is not None:
            self._engine.dispose()
            logger.info("Disconnected from %s database", self.driver)
        self._engine = None
        self._session_factory = None

    @contextmanager
    def session(self) -> Iterator[Session]:
        """Provide a transactional session scope."""
        if self._session_factory is None:
            raise DatabaseError("Database is not connected. Call connect() first.")

        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def execute(self, sql: str, params: dict[str, Any] | None = None) -> None:
        """Execute a raw SQL statement within a connection."""
        try:
            with self.engine.begin() as connection:
                connection.execute(text(sql), params or {})
        except Exception as exc:
            raise DatabaseError("Failed to execute SQL", cause=exc) from exc

    def _build_engine_args(self) -> tuple[str, dict[str, Any]]:
        if self.driver in _SQLITE_DRIVERS:
            if self.path is None:
                raise ConfigurationError(
                    "SQLite driver requires paths.database_file / database path"
                )
            self.path.parent.mkdir(parents=True, exist_ok=True)
            return (
                f"sqlite:///{self.path.as_posix()}",
                {
                    "check_same_thread": self.settings.check_same_thread,
                    "timeout": self.settings.timeout_seconds,
                },
            )

        if self.driver in _POSTGRES_DRIVERS:
            if not self.url:
                raise ConfigurationError(
                    "PostgreSQL driver requires database.url "
                    "(e.g. postgresql+psycopg://user:pass@host:5432/pip)"
                )
            return self.url, {}

        raise ConfigurationError(
            f"Unsupported database driver: {self.driver!r} "
            "(expected sqlite or postgresql)"
        )


def _set_sqlite_pragma(
    dbapi_connection: object,
    _connection_record: object,
) -> None:
    """Enable foreign key enforcement for each SQLite connection."""
    cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_database(config: AppConfig) -> Database:
    """Create and connect a :class:`Database` from application config."""
    config.ensure_directories()
    database = Database(
        config.database_path,
        settings=config.database,
        url=config.database.url,
    )
    database.connect()
    return database
