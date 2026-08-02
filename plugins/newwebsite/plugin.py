"""NewWebsite importer plugin.

```
Downloader
 ↓
Parser
 ↓
Extractor
 ↓
Normalizer
 ↓
Validator
 ↓
Importer
```

Package layout::

```
plugins/
  newwebsite/
    plugin.py
    parser.py
    extractor.py
    normalizer.py
    validator.py
```
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from newwebsite.extractor import NewWebsiteExtractor
from newwebsite.normalizer import NewWebsiteNormalizer
from newwebsite.parser import PARSER_VERSION, NewWebsiteParser
from newwebsite.stage_validator import NewWebsiteStageValidator
from newwebsite.validator import NewWebsiteValidator
from profile_intelligence.application.pipeline.plugin_pipeline import PluginPipeline
from profile_intelligence.core.logging import get_logger
from profile_intelligence.core.types import PathLike
from profile_intelligence.infrastructure.importers.base import ImportResult
from profile_intelligence.infrastructure.importers.profile_importer import (
    ProfileImporter,
    ProfileParseOutcome,
)

logger = get_logger("importers.external.newwebsite")


class NewWebsiteImporter(ProfileImporter):
    """NewWebsite HTML/JSON importer via :class:`PluginPipeline`.

    Dependencies are injectable for tests:

    - :class:`NewWebsiteParser`
    - :class:`NewWebsiteExtractor`
    - :class:`NewWebsiteNormalizer`
    - :class:`NewWebsiteValidator`
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
        pipeline: PluginPipeline | None = None,
    ) -> None:
        self._parser = parser or NewWebsiteParser()
        self._extractor = extractor or NewWebsiteExtractor()
        self._validator = validator or NewWebsiteValidator()
        self._normalizer = normalizer or NewWebsiteNormalizer()
        self._pipeline = pipeline or PluginPipeline(
            parser=self._parser,
            extractor=self._extractor,
            normalizer=self._normalizer,
            validator=NewWebsiteStageValidator(self._validator),
        )

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
        """Parser → Extractor → Normalizer → Validator → records."""
        if not (
            self.matches_source_marker(path)
            or path.name.lower().endswith((".newwebsite.html", ".newwebsite.json"))
        ):
            try:
                document = self._parser.parse(path)
            except Exception as exc:  # noqa: BLE001 — sniff/parse must not crash import
                return ImportResult.failure(f"Unexpected NewWebsite parse error: {exc}")
            if not self._parser.looks_like_newwebsite(document):
                return ImportResult.failure(
                    "Document does not look like a NewWebsite profile"
                )

        result = self._pipeline.run(path)
        for warning in result.warnings:
            logger.warning("NewWebsite %s: %s", path.name, warning)
        if not result.records:
            message = (
                result.errors[0]
                if result.errors
                else "No valid NewWebsite profiles found (name is required)"
            )
            return ImportResult.failure(message)

        logger.info(
            "NewWebsite imported %s records=%d skipped=%d stages=%s",
            path.name,
            len(result.records),
            result.skipped,
            "→".join(result.stages_run),
        )
        return list(result.records), result.skipped
