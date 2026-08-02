"""Local profile search over SQLite."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import or_, select

from profile_intelligence.core.exceptions import SearchError
from profile_intelligence.core.logging import get_logger
from profile_intelligence.infrastructure.database.connection import Database
from profile_intelligence.infrastructure.database.models import Profile

logger = get_logger(__name__)


class ProfileSearchService:
    """Case-insensitive substring search across key profile fields."""

    def __init__(self, database: Database, *, default_limit: int = 50) -> None:
        self._database = database
        self._default_limit = default_limit

    def search(
        self,
        query: str,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> Sequence[Profile]:
        """Search profiles by name, email, org, title, location, tags, or notes."""
        needle = query.strip()
        if not needle:
            raise SearchError("Search query must not be empty")
        if offset < 0:
            raise SearchError("offset must be non-negative")

        max_rows = self._default_limit if limit is None else limit
        if max_rows < 0:
            raise SearchError("limit must be non-negative")

        pattern = f"%{needle}%"
        statement = (
            select(Profile)
            .where(
                or_(
                    Profile.display_name.ilike(pattern),
                    Profile.email.ilike(pattern),
                    Profile.organization.ilike(pattern),
                    Profile.title.ilike(pattern),
                    Profile.location.ilike(pattern),
                    Profile.tags.ilike(pattern),
                    Profile.notes.ilike(pattern),
                    Profile.external_id.ilike(pattern),
                    Profile.source.ilike(pattern),
                )
            )
            .order_by(Profile.display_name.asc(), Profile.id.asc())
            .offset(offset)
            .limit(max_rows)
        )
        try:
            with self._database.session() as session:
                return list(session.scalars(statement).all())
        except SearchError:
            raise
        except Exception as exc:
            raise SearchError(
                f"Search failed for query={query!r}",
                cause=exc,
            ) from exc
