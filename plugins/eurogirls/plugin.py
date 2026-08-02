"""EuroGirls Safari ``.webarchive`` importer plugin.

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
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from eurogirls.extractor import EuroGirlsExtractor
from eurogirls.normalizer import EuroGirlsNormalizer
from eurogirls.parser import PARSER_VERSION, WebArchiveParser
from eurogirls.validator import EuroGirlsValidator
from profile_intelligence.application.pipeline.plugin_pipeline import PluginPipeline
from profile_intelligence.core.logging import get_logger
from profile_intelligence.core.types import PathLike
from profile_intelligence.infrastructure.importers.base import ImportResult
from profile_intelligence.infrastructure.importers.profile_importer import (
    ProfileImporter,
    ProfileParseOutcome,
)

logger = get_logger("importers.external.eurogirls")


class EuroGirlsImporter(ProfileImporter):
    """EuroGirls ``.webarchive`` importer via :class:`PluginPipeline`.

    Dependencies are injectable for tests:

    - :class:`WebArchiveParser`
    - :class:`EuroGirlsExtractor`
    - :class:`EuroGirlsNormalizer`
    - :class:`EuroGirlsValidator`
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
        validator: EuroGirlsValidator | None = None,
        pipeline: PluginPipeline | None = None,
    ) -> None:
        self._parser = parser or WebArchiveParser()
        self._extractor = extractor or EuroGirlsExtractor()
        self._normalizer = normalizer or EuroGirlsNormalizer()
        self._validator = validator or EuroGirlsValidator()
        self._pipeline = pipeline or PluginPipeline(
            parser=self._parser,
            extractor=self._extractor,
            normalizer=self._normalizer,
            validator=self._validator,
        )

    def can_handle(self, path: PathLike) -> bool:
        """Accept EuroGirls-marked or EuroGirls-content webarchives."""
        resolved = Path(path)
        if not self.matches_extension(resolved):
            return False
        if self.matches_source_marker(resolved):
            return True
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
        """Parser → Extractor → Normalizer → Validator → records."""
        if not self.matches_source_marker(path):
            try:
                archive = self._parser.parse(path)
            except Exception as exc:  # noqa: BLE001 — sniff/parse must not crash import
                return ImportResult.failure(
                    f"Unexpected EuroGirls parse error: {exc}"
                )
            if not self._parser.looks_like_eurogirls(archive):
                return ImportResult.failure(
                    "Document is not a EuroGirls profile webarchive"
                )

        result = self._pipeline.run(path)
        for warning in result.warnings:
            logger.warning("EuroGirls %s: %s", path.name, warning)
        if not result.records:
            message = (
                result.errors[0]
                if result.errors
                else "Rejected incomplete EuroGirls document (name is required)"
            )
            return ImportResult.failure(message)

        record = result.records[0]
        logger.info(
            "EuroGirls imported %s name=%r id=%r rates=%d services=%d photos=%d",
            path.name,
            record.get("display_name"),
            record.get("profile_id"),
            len(record.get("rates") or []),
            len(record.get("services") or []),
            len(record.get("photos") or []),
        )
        return list(result.records), result.skipped
