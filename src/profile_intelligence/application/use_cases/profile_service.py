"""Profile application service for list/export/rescore workflows."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import cast

from profile_intelligence.core.logging import get_logger
from profile_intelligence.core.types import PathLike
from profile_intelligence.domain.interfaces.repositories import (
    IProfileRepository,
    ProfileEntity,
)
from profile_intelligence.infrastructure.excel.exporter import ExcelExporter
from profile_intelligence.infrastructure.scoring.confidence import ConfidenceScorer
from profile_intelligence.infrastructure.search.service import ProfileSearchService

logger = get_logger(__name__)


class ProfileService:
    """High-level profile operations used by the CLI."""

    def __init__(
        self,
        repository: IProfileRepository,
        search_service: ProfileSearchService,
        exporter: ExcelExporter,
        scorer: ConfidenceScorer | None = None,
    ) -> None:
        self._repository = repository
        self._search = search_service
        self._excel = exporter
        self._scorer = scorer or ConfidenceScorer()

    def list_profiles(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[ProfileEntity]:
        """Return a page of profiles."""
        return self._repository.list_all(limit=limit, offset=offset)

    def count(self) -> int:
        """Return total profile count."""
        return self._repository.count()

    def search(
        self,
        query: str,
        *,
        limit: int | None = None,
    ) -> Sequence[ProfileEntity]:
        """Search profiles."""
        return cast(
            Sequence[ProfileEntity],
            self._search.search(query, limit=limit),
        )

    def export_excel(
        self,
        output_path: PathLike | None = None,
        *,
        limit: int = 10_000,
    ) -> Path:
        """Export profiles to Excel."""
        profiles = self._repository.list_all(limit=limit, offset=0)
        return self._excel.export(profiles, output_path)

    def rescore_all(self, *, limit: int = 100_000) -> int:
        """Recompute Confidence Scores (0-100) for all profiles."""
        profiles = self._repository.list_all(limit=limit, offset=0)
        scores = {
            profile.id: self._scorer.score(profile)
            for profile in profiles
            if profile.id is not None
        }
        updated = self._repository.update_scores(scores)
        logger.info("Rescored %d profile(s)", updated)
        return updated
