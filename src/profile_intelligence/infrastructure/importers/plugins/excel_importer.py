"""Built-in Excel (.xlsx) importer plugin."""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

from openpyxl import load_workbook

from profile_intelligence.core.exceptions import ImporterError
from profile_intelligence.core.logging import get_logger
from profile_intelligence.infrastructure.importers.base import ImportResult, RawRecord
from profile_intelligence.infrastructure.importers.profile_importer import (
    ProfileImporter,
    ProfileParseOutcome,
)

logger = get_logger(__name__)


class ExcelImporter(ProfileImporter):
    """Import profile rows from the first sheet of an Excel workbook."""

    name: ClassVar[str] = "excel"
    description: ClassVar[str] = "Excel .xlsx profile importer (first sheet)"
    supported_extensions: ClassVar[tuple[str, ...]] = (".xlsx",)

    def parse_profiles(self, path: Path, **options: object) -> ProfileParseOutcome:
        sheet_name = options.get("sheet_name")
        try:
            workbook = load_workbook(
                filename=path,
                read_only=True,
                data_only=True,
            )
        except Exception as exc:
            raise ImporterError(
                f"Failed to open Excel workbook: {path}",
                cause=exc,
            ) from exc

        try:
            if sheet_name is not None:
                worksheet = workbook[str(sheet_name)]
            else:
                worksheet = workbook[workbook.sheetnames[0]]
            active_sheet_title = worksheet.title

            rows = worksheet.iter_rows(values_only=True)
            try:
                header_row = next(rows)
            except StopIteration:
                return ImportResult.failure("Excel sheet is empty")

            headers = [
                str(cell).strip() if cell is not None else f"column_{index}"
                for index, cell in enumerate(header_row, start=1)
            ]
            if not any(headers):
                return ImportResult.failure("Excel sheet has no header row")

            records: list[RawRecord] = []
            skipped = 0
            for row in rows:
                values = list(row)
                if all(
                    value is None or str(value).strip() == "" for value in values
                ):
                    skipped += 1
                    continue
                record: dict[str, Any] = {}
                for index, header in enumerate(headers):
                    value = values[index] if index < len(values) else None
                    record[header] = value
                records.append(record)
        finally:
            workbook.close()

        logger.debug(
            "Parsed Excel %s sheet=%s records=%d skipped=%d",
            path,
            active_sheet_title,
            len(records),
            skipped,
        )
        # Preserve sheet name in metadata via ImportResult path.
        return ImportResult.from_records(
            records,
            skipped=skipped,
            metadata={
                "path": str(path),
                "plugin": self.name,
                "sheet": active_sheet_title,
            },
        )
