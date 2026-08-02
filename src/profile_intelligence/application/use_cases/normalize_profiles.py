"""Normalizer stage: raw records → profile drafts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from profile_intelligence.core.logging import get_logger
from profile_intelligence.domain.entities.profile import ProfileDraft, ProfileExtractor
from profile_intelligence.infrastructure.importers.base import RawRecord

logger = get_logger(__name__)


class ProfileNormalizer:
    """Normalize loosely-named raw rows into :class:`ProfileDraft` values."""

    def __init__(self, extractor: ProfileExtractor | None = None) -> None:
        self._extractor = extractor or ProfileExtractor()

    def normalize(
        self,
        record: Mapping[str, object],
        *,
        source_override: str | None = None,
    ) -> ProfileDraft:
        """Normalize a single raw record."""
        return self._extractor.extract(record, source_override=source_override)

    def normalize_many(
        self,
        records: Sequence[RawRecord] | Sequence[Mapping[str, object]],
        *,
        source_override: str | None = None,
    ) -> tuple[list[ProfileDraft], list[str]]:
        """Normalize many records; return drafts and per-row errors."""
        drafts, errors = self._extractor.extract_many(
            list(records),
            source_override=source_override,
        )
        logger.debug(
            "Normalizer stage: drafts=%d errors=%d",
            len(drafts),
            len(errors),
        )
        return drafts, errors
