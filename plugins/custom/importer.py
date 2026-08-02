"""Template importer for private or one-off export formats.

Copy this package or edit in place. By default it handles ``*.custom.json``
files containing a JSON array of profile objects.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, ClassVar

from profile_intelligence.core.exceptions import ImporterError
from profile_intelligence.core.logging import get_logger
from profile_intelligence.core.types import PathLike
from profile_intelligence.infrastructure.importers.base import ImportResult, RawRecord
from profile_intelligence.infrastructure.importers.profile_importer import (
    ProfileImporter,
    ProfileParseOutcome,
)

logger = get_logger("importers.external.custom")


class CustomImporter(ProfileImporter):
    """Example external importer for ``*.custom.json`` arrays."""

    name: ClassVar[str] = "custom"
    description: ClassVar[str] = (
        "Custom JSON array importer (template for private formats)"
    )
    supported_extensions: ClassVar[tuple[str, ...]] = (".json",)
    source_markers: ClassVar[tuple[str, ...]] = ("custom",)
    require_source_marker: ClassVar[bool] = True

    def can_handle(self, path: PathLike) -> bool:
        resolved = Path(path)
        name = resolved.name.lower()
        if name.endswith(".custom.json"):
            return True
        return super().can_handle(resolved)

    def parse_profiles(self, path: Path, **options: object) -> ProfileParseOutcome:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ImporterError(
                f"Failed to read custom JSON import: {path}",
                cause=exc,
            ) from exc

        if isinstance(payload, dict):
            rows = payload.get("profiles") or payload.get("records") or [payload]
        elif isinstance(payload, list):
            rows = payload
        else:
            return ImportResult.failure(
                "Custom JSON must be an object or array of profile objects"
            )

        records: list[RawRecord] = []
        skipped = 0
        for row in rows:
            if not isinstance(row, dict):
                skipped += 1
                continue
            materialised: dict[str, Any] = dict(row)
            if self.is_empty_row(materialised):
                skipped += 1
                continue
            records.append(materialised)

        logger.debug(
            "Parsed custom JSON %s: records=%d skipped=%d",
            path,
            len(records),
            skipped,
        )
        return records, skipped
