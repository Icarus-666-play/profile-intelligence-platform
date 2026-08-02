"""Built-in Excel (.xlsx) importer plugin."""

from __future__ import annotations

from typing import Any, ClassVar

from openpyxl import load_workbook

from profile_intelligence.core.exceptions import ImporterError
from profile_intelligence.core.types import PathLike
from profile_intelligence.importers.base import ImporterPlugin, ImportResult


class ExcelImporter(ImporterPlugin):
    """Import profile rows from the first sheet of an Excel workbook."""

    name: ClassVar[str] = "excel"
    description: ClassVar[str] = "Excel .xlsx profile importer (first sheet)"
    supported_extensions: ClassVar[tuple[str, ...]] = (".xlsx",)

    def can_handle(self, path: PathLike) -> bool:
        return self.matches_extension(path)

    def import_file(self, path: PathLike, **options: object) -> ImportResult:
        resolved = self.validate_path(path)
        sheet_name = options.get("sheet_name")
        try:
            workbook = load_workbook(
                filename=resolved,
                read_only=True,
                data_only=True,
            )
        except Exception as exc:
            raise ImporterError(
                f"Failed to open Excel workbook: {resolved}",
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

            records: list[dict[str, Any]] = []
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

        return ImportResult.from_records(
            records,
            skipped=skipped,
            metadata={
                "path": str(resolved),
                "plugin": self.name,
                "sheet": active_sheet_title,
            },
        )
