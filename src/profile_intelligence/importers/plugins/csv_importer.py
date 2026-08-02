"""Built-in CSV importer plugin."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import ClassVar

from profile_intelligence.core.exceptions import ImporterError
from profile_intelligence.core.logging import get_logger
from profile_intelligence.importers.base import ImportResult, RawRecord
from profile_intelligence.importers.profile_importer import (
    ProfileImporter,
    ProfileParseOutcome,
)

logger = get_logger(__name__)


class CsvImporter(ProfileImporter):
    """Import profile rows from a UTF-8 CSV file with a header row."""

    name: ClassVar[str] = "csv"
    description: ClassVar[str] = "CSV profile importer (header row required)"
    supported_extensions: ClassVar[tuple[str, ...]] = (".csv",)

    def parse_profiles(self, path: Path, **options: object) -> ProfileParseOutcome:
        encoding = str(options.get("encoding", "utf-8-sig"))
        try:
            with path.open(encoding=encoding, newline="") as handle:
                reader = csv.DictReader(handle)
                if not reader.fieldnames:
                    return ImportResult.failure("CSV file has no header row")
                records: list[RawRecord] = []
                skipped = 0
                for row in reader:
                    materialised = dict(row)
                    if self.is_empty_row(materialised):
                        skipped += 1
                        continue
                    records.append(materialised)
        except UnicodeDecodeError as exc:
            raise ImporterError(
                f"Failed to decode CSV as {encoding}",
                cause=exc,
            ) from exc
        except OSError as exc:
            raise ImporterError(
                f"Failed to read CSV file: {path}",
                cause=exc,
            ) from exc

        logger.debug(
            "Parsed CSV %s: records=%d skipped=%d",
            path,
            len(records),
            skipped,
        )
        return records, skipped
