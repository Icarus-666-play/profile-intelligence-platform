"""SQLite connection management via SQLAlchemy."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from profile_intelligence.core.config import AppConfig, DatabaseSection
from profile_intelligence.core.exceptions import DatabaseError
from profile_intelligence.core.logging import get_logger
from profile_intelligence.core.types import PathLike

logger = get_logger(__name__)


class Database:
    """Owns the SQLAlchemy engine and session factory for PIP."""

    def __init__(
        self,
        database_path: PathLike,
        settings: DatabaseSection | None = None,
    ) -> None:
        self.path = Path(database_path)
        self.settings = settings or DatabaseSection()
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
        """Create the engine and enable SQLite pragmas."""
        if self._engine is not None:
            return

        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            url = f"sqlite:///{self.path.as_posix()}"
            self._engine = create_engine(
                url,
                echo=self.settings.echo_sql,
                connect_args={
                    "check_same_thread": self.settings.check_same_thread,
                    "timeout": self.settings.timeout_seconds,
                },
                future=True,
            )
            if self.settings.foreign_keys:
                event.listen(self._engine, "connect", _set_sqlite_pragma)

            self._session_factory = sessionmaker(
                bind=self._engine,
                autoflush=False,
                autocommit=False,
                expire_on_commit=False,
                future=True,
            )
            # Verify connectivity
            with self._engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            logger.info("Connected to SQLite database at %s", self.path)
        except DatabaseError:
            raise
        except Exception as exc:
            self._engine = None
            self._session_factory = None
            raise DatabaseError(
                f"Failed to connect to database: {self.path}",
                cause=exc,
            ) from exc

    def disconnect(self) -> None:
        """Dispose the engine and clear the session factory."""
        if self._engine is not None:
            self._engine.dispose()
            logger.info("Disconnected from SQLite database at %s", self.path)
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
    database = Database(config.database_path, settings=config.database)
    database.connect()
    return database
