# Importer Plugin Framework

Importers convert external files into raw row records. The import service then
extracts, scores, and persists profiles.

## Built-in plugins (Milestone 1)

| Plugin | Extensions | Notes |
|--------|------------|-------|
| `csv` | `.csv` | UTF-8 CSV with header row |
| `excel` | `.xlsx` | First worksheet (or `--` sheet via options) |

## Interface

Subclass `ImporterPlugin` and return `ImportResult.from_records(...)`:

```python
from typing import ClassVar
from profile_intelligence.importers import ImporterPlugin, ImportResult

class MyImporter(ImporterPlugin):
    name: ClassVar[str] = "my_source"
    description: ClassVar[str] = "Imports from my format"
    supported_extensions: ClassVar[tuple[str, ...]] = (".csv",)

    def can_handle(self, path) -> bool:
        return self.matches_extension(path)

    def import_file(self, path, **options: object) -> ImportResult:
        self.validate_path(path)
        return ImportResult.from_records([{"name": "Ada"}])
```

## Header aliases

`ProfileExtractor` recognizes common column names, including:

- name / display_name / full_name
- email / e-mail
- phone / mobile
- title / job_title / role
- organization / company
- location / city
- tags / skills
- external_id / id
- notes / comments

## Discovery

`ImporterRegistry.discover()`:

1. Loads built-in modules under `profile_intelligence.importers.plugins`
2. Optionally loads `*.py` modules from the configured `plugins/` directory
3. Filters by `importers.enabled` when that list is non-empty

## CLI

```bash
python -m profile_intelligence importers
python -m profile_intelligence import path/to/file.csv
python -m profile_intelligence import path/to/file.xlsx --source crm
```
