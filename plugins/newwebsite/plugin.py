"""NewWebsite importer plugin.

```
plugins/
  newwebsite/
    plugin.py
    parser.py
    extractor.py
    normalizer.py
    validator.py
```

Pipeline::

    HTML / JSON
         ↓
    Parser
         ↓
    Extractor
         ↓
    Validator
         ↓
    Normalizer
         ↓
    Domain Profile → repository
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from newwebsite.extractor import NewWebsiteExtractor
from newwebsite.normalizer import NewWebsiteNormalizer
from newwebsite.parser import PARSER_VERSION, NewWebsiteParser
from newwebsite.validator import NewWebsiteValidator
from profile_intelligence.core.exceptions import ImporterError
from profile_intelligence.core.logging import get_logger
from profile_intelligence.core.types import PathLike
from profile_intelligence.infrastructure.importers.base import ImportResult
from profile_intelligence.infrastructure.importers.profile_importer import (
    ProfileImporter,
    ProfileParseOutcome,
)

logger = get_logger("importers.external.newwebsite")


class NewWebsiteImporter(ProfileImporter):
    """Scaffold / production-ready NewWebsite HTML+JSON importer.

    Dependencies are injectable for tests:

    - :class:`NewWebsiteParser`
    - :class:`NewWebsiteExtractor`
    - :class:`NewWebsiteValidator`
    - :class:`NewWebsiteNormalizer`
    """

    name: ClassVar[str] = "newwebsite"
    description: ClassVar[str] = (
        f"NewWebsite HTML/JSON importer (parser v{PARSER_VERSION})"
    )
    supported_extensions: ClassVar[tuple[str, ...]] = (
        ".html",
        ".htm",
        ".json",
    )
    source_markers: ClassVar[tuple[str, ...]] = ("newwebsite",)
    require_source_marker: ClassVar[bool] = False

    def __init__(
        self,
        parser: NewWebsiteParser | None = None,
        extractor: NewWebsiteExtractor | None = None,
        validator: NewWebsiteValidator | None = None,
        normalizer: NewWebsiteNormalizer | None = None,
    ) -> None:
        self._parser = parser or NewWebsiteParser()
        self._extractor = extractor or NewWebsiteExtractor()
        self._validator = validator or NewWebsiteValidator()
        self._normalizer = normalizer or NewWebsiteNormalizer()

    def can_handle(self, path: PathLike) -> bool:
        """Accept NewWebsite-marked files or sniffable NewWebsite content."""
        resolved = Path(path)
        if not self.matches_extension(resolved):
            return False
        if self.matches_source_marker(resolved):
            return True
        name = resolved.name.lower()
        if name.endswith(".newwebsite.html") or name.endswith(".newwebsite.json"):
            return True
        try:
            document = self._parser.parse(resolved)
        except Exception as exc:  # noqa: BLE001 - sniff must never raise
            logger.debug(
                "NewWebsite can_handle sniff failed for %s: %s",
                resolved,
                exc,
            )
            return False
        return self._parser.looks_like_newwebsite(document)

    def parse_profiles(
        self,
        path: Path,
        **options: object,
    ) -> ProfileParseOutcome:
        """Parse one NewWebsite source into normalized raw records."""
        try:
            document = self._parser.parse(path)
        except ImporterError as exc:
            logger.warning("NewWebsite parse failed for %s: %s", path, exc)
            return ImportResult.failure(str(exc))
        except Exception as exc:
            logger.exception("Unexpected NewWebsite parse error for %s", path)
            return ImportResult.failure(
                f"Unexpected NewWebsite parse error: {exc}"
            )

        if not document.is_complete:
            return ImportResult.failure("Incomplete NewWebsite document")

        if not (
            self.matches_source_marker(path)
            or path.name.lower().endswith((".newwebsite.html", ".newwebsite.json"))
            or self._parser.looks_like_newwebsite(document)
        ):
            return ImportResult.failure(
                "Document does not look like a NewWebsite profile"
            )

        records = []
        skipped = 0
        for extracted in self._extractor.extract_many(document):
            validation = self._validator.validate(extracted)
            for warning in validation.warnings:
                logger.warning("NewWebsite %s: %s", path.name, warning)
            if not validation.is_valid:
                skipped += 1
                continue
            try:
                records.append(self._normalizer.normalize(extracted, document))
            except Exception as exc:
                logger.exception("NewWebsite normalize failed for %s", path)
                return ImportResult.failure(
                    f"NewWebsite normalize failed: {exc}"
                )

        if not records:
            return ImportResult.failure(
                "No valid NewWebsite profiles found (name is required)"
            )

        logger.info(
            "NewWebsite imported %s records=%d skipped=%d",
            path.name,
            len(records),
            skipped,
        )
        return records, skipped
