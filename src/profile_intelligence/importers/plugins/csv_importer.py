"""Built-in CSV importer plugin."""

from __future__ import annotations

import csv
from typing import Any, ClassVar

from profile_intelligence.core.exceptions import ImporterError
from profile_intelligence.core.types import PathLike
from profile_intelligence.importers.base import ImporterPlugin, ImportResult


class CsvImporter(ImporterPlugin):
    """Import profile rows from a UTF-8 CSV file with a header row."""

    name: ClassVar[str] = "csv"
    description: ClassVar[str] = "CSV profile importer (header row required)"
    supported_extensions: ClassVar[tuple[str, ...]] = (".csv",)

    def can_handle(self, path: PathLike) -> bool:
        return self.matches_extension(path)

    def import_file(self, path: PathLike, **options: object) -> ImportResult:
        resolved = self.validate_path(path)
        encoding = str(options.get("encoding", "utf-8-sig"))
        try:
            with resolved.open(encoding=encoding, newline="") as handle:
                reader = csv.DictReader(handle)
                if not reader.fieldnames:
                    return ImportResult.failure("CSV file has no header row")
                records: list[dict[str, Any]] = []
                skipped = 0
                for row in reader:
                    if all(
                        value is None or str(value).strip() == ""
                        for value in row.values()
                    ):
                        skipped += 1
                        continue
                    records.append(dict(row))
        except UnicodeDecodeError as exc:
            raise ImporterError(
                f"Failed to decode CSV as {encoding}",
                cause=exc,
            ) from exc
        except OSError as exc:
            raise ImporterError(
                f"Failed to read CSV file: {resolved}",
                cause=exc,
            ) from exc

        return ImportResult.from_records(
            records,
            skipped=skipped,
            metadata={"path": str(resolved), "plugin": self.name},
        )
