"""Template importer for private or one-off export formats.

Copy this package or edit in place. By default it handles ``*.custom.json``
files containing a JSON array of profile objects.
"""

from __future__ import annotations

import json
from typing import Any, ClassVar

from profile_intelligence.core.exceptions import ImporterError
from profile_intelligence.core.logging import get_logger
from profile_intelligence.core.types import PathLike
from profile_intelligence.importers.base import ImporterPlugin, ImportResult

logger = get_logger("importers.external.custom")


class CustomImporter(ImporterPlugin):
    """Example external importer for ``*.custom.json`` arrays."""

    name: ClassVar[str] = "custom"
    description: ClassVar[str] = (
        "Custom JSON array importer (template for private formats)"
    )
    supported_extensions: ClassVar[tuple[str, ...]] = (".json",)

    def can_handle(self, path: PathLike) -> bool:
        from pathlib import Path

        resolved = Path(path)
        name = resolved.name.lower()
        stem = resolved.stem.lower()
        return name.endswith(".custom.json") or (
            self.matches_extension(resolved)
            and (
                stem == "custom"
                or stem.startswith("custom_")
                or stem.endswith("_custom")
            )
        )

    def import_file(self, path: PathLike, **options: object) -> ImportResult:
        resolved = self.validate_path(path)
        try:
            payload = json.loads(resolved.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ImporterError(
                f"Failed to read custom JSON import: {resolved}",
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

        records: list[dict[str, Any]] = []
        skipped = 0
        for row in rows:
            if not isinstance(row, dict):
                skipped += 1
                continue
            records.append(dict(row))

        logger.debug(
            "Parsed custom JSON %s: records=%d skipped=%d",
            resolved,
            len(records),
            skipped,
        )
        return ImportResult.from_records(
            records,
            skipped=skipped,
            metadata={"path": str(resolved), "plugin": self.name},
        )
