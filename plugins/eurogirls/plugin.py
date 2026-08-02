"""EuroGirls Safari ``.webarchive`` importer plugin.

Pipeline::

    .webarchive
         ↓
    RawDocument (via ImportPipeline / DocumentParser)
         ↓
    BeautifulSoup Parser  (this plugin)
         ↓
    Extract structured data
         ↓
    Normalize
         ↓
    Validate
         ↓
    Domain Profile → SQLiteRepository → SQLite
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from eurogirls.extractor import EuroGirlsExtractor, ExtractedProfile
from eurogirls.normalizer import EuroGirlsNormalizer
from eurogirls.parser import PARSER_VERSION, WebArchiveParser
from profile_intelligence.core.exceptions import ImporterError
from profile_intelligence.core.logging import get_logger
from profile_intelligence.core.types import PathLike
from profile_intelligence.infrastructure.importers.base import ImportResult
from profile_intelligence.infrastructure.importers.profile_importer import (
    ProfileImporter,
    ProfileParseOutcome,
)

logger = get_logger("importers.external.eurogirls")


class EuroGirlsImporter(ProfileImporter):
    """Production EuroGirls ``.webarchive`` importer.

    Dependencies are injectable for tests / SOLID composition:

    - :class:`WebArchiveParser`
    - :class:`EuroGirlsExtractor`
    - :class:`EuroGirlsNormalizer`
    """

    name: ClassVar[str] = "eurogirls"
    description: ClassVar[str] = (
        "EuroGirls Safari .webarchive importer "
        f"(parser v{PARSER_VERSION})"
    )
    supported_extensions: ClassVar[tuple[str, ...]] = (".webarchive",)
    source_markers: ClassVar[tuple[str, ...]] = ("eurogirls",)
    require_source_marker: ClassVar[bool] = False

    def __init__(
        self,
        parser: WebArchiveParser | None = None,
        extractor: EuroGirlsExtractor | None = None,
        normalizer: EuroGirlsNormalizer | None = None,
    ) -> None:
        self._parser = parser or WebArchiveParser()
        self._extractor = extractor or EuroGirlsExtractor()
        self._normalizer = normalizer or EuroGirlsNormalizer()

    def can_handle(self, path: PathLike) -> bool:
        """Accept EuroGirls-marked or EuroGirls-content webarchives."""
        resolved = Path(path)
        if not self.matches_extension(resolved):
            return False
        if self.matches_source_marker(resolved):
            return True
        # Content sniff — never crash on unreadable files.
        try:
            parsed = self._parser.parse(resolved)
        except Exception as exc:  # noqa: BLE001 — sniff must never raise
            logger.debug(
                "EuroGirls can_handle sniff failed for %s: %s",
                resolved,
                exc,
            )
            return False
        return self._parser.looks_like_eurogirls(parsed)

    def parse_profiles(
        self,
        path: Path,
        **options: object,
    ) -> ProfileParseOutcome:
        """Parse one EuroGirls webarchive into a normalized raw record."""
        try:
            archive = self._parser.parse(path)
        except ImporterError as exc:
            logger.warning("EuroGirls parse failed for %s: %s", path, exc)
            return ImportResult.failure(str(exc))
        except Exception as exc:
            logger.exception("Unexpected EuroGirls parse error for %s", path)
            return ImportResult.failure(
                f"Unexpected EuroGirls parse error: {exc}"
            )

        if not archive.is_complete:
            logger.warning("Incomplete webarchive document: %s", path)
            return ImportResult.failure(
                "Incomplete webarchive document (empty HTML)"
            )

        if not (
            self.matches_source_marker(path)
            or self._parser.looks_like_eurogirls(archive)
        ):
            logger.warning(
                "Document does not look like a EuroGirls profile: %s",
                path,
            )
            return ImportResult.failure(
                "Document is not a EuroGirls profile webarchive"
            )

        try:
            extracted = self._extractor.extract(archive)
        except Exception as exc:
            logger.exception("EuroGirls extraction failed for %s", path)
            return ImportResult.failure(f"EuroGirls extraction failed: {exc}")

        for warning in extracted.warnings:
            logger.warning("EuroGirls %s: %s", path.name, warning)

        if not self._validate_extracted(extracted):
            return ImportResult.failure(
                "Rejected incomplete EuroGirls document "
                "(name is required)"
            )

        try:
            record = self._normalizer.normalize(extracted, archive)
        except Exception as exc:
            logger.exception("EuroGirls normalize failed for %s", path)
            return ImportResult.failure(f"EuroGirls normalize failed: {exc}")

        logger.info(
            "EuroGirls imported %s name=%r id=%r rates=%d services=%d photos=%d",
            path.name,
            record.get("display_name"),
            record.get("profile_id"),
            len(record.get("rates") or []),
            len(record.get("services") or []),
            len(record.get("photos") or []),
        )
        return [record], 0

    @staticmethod
    def _validate_extracted(extracted: ExtractedProfile) -> bool:
        """Reject incomplete documents; warnings are non-fatal."""
        return extracted.is_complete
