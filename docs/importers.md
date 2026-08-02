# Importer Plugin Framework

Importers convert external files into raw row records. Persistence goes through
the staged pipeline (`config/settings.yaml`):

```
pipeline:
  - parser
  - normalizer
  - validator
  - duplicate_detector
  - scorer
  - repository
```

`ImportService.import_path()` / `ImportPipeline.process()` run the full chain
end-to-end via `ProcessingChain`. Parser uses a `ProfileImporter` plugin.

## Built-in plugins (Milestone 1)

| Plugin | Extensions | Notes |
|--------|------------|-------|
| `csv` | `.csv` | UTF-8 CSV with header row |
| `excel` | `.xlsx` | First worksheet (or `--` sheet via options) |
| `webarchive` | `.webarchive` | Safari webarchive → HTML profile fields |

## External: EuroGirls (Sprint 1)

Package: `plugins/eurogirls/`

| File | Role |
|------|------|
| `plugin.py` | `EuroGirlsImporter` (`ProfileImporter`) |
| `parser.py` | Safari `.webarchive` → HTML + subresources |
| `extractor.py` | BeautifulSoup → general / physical / rates / services / photos |
| `normalizer.py` | Structured data → platform `RawRecord` |
| `tests.py` | Unit + pipeline tests |

Pipeline:

```
.webarchive → RawDocument → BeautifulSoup Parser → Extract → Normalize
→ Validate → Domain Profile → SQLiteRepository → SQLite
```

Sample archives: `samples/eurogirls/*.webarchive`

```bash
pip-app import samples/eurogirls/sophia_eurogirls.webarchive --plugin eurogirls
```

## Interface

Prefer subclassing `ProfileImporter` (builds on `ImporterPlugin`) and implement
`parse_profiles()`:

```python
from pathlib import Path
from typing import ClassVar
from profile_intelligence.infrastructure.importers import ProfileImporter

class MyImporter(ProfileImporter):
    name: ClassVar[str] = "my_source"
    description: ClassVar[str] = "Imports from my format"
    supported_extensions: ClassVar[tuple[str, ...]] = (".csv",)
    source_markers: ClassVar[tuple[str, ...]] = ("my_source",)  # optional
    require_source_marker: ClassVar[bool] = True                # optional

    def parse_profiles(self, path: Path, **options: object):
        # return (records, skipped) or ImportResult.failure(...)
        return [{"name": "Ada"}], 0
```

`ProfileImporter` provides:

- `can_handle()` from extensions + optional source filename markers
- `import_file()` wrapping parse output in `ImportResult`
- helpers: `is_empty_row()`, `matches_source_marker()`, `build_metadata()`

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

1. Loads built-in modules under `profile_intelligence.infrastructure.importers.plugins`
2. Loads top-level `*.py` modules from the configured `plugins/` directory
3. Loads each `plugins/<name>/` package (for example `eurogirls/`, `eros/`, `custom/`)
4. Filters by `importers.enabled` when that list is non-empty

## External plugin packages

Shipped scaffolds under `plugins/`:

| Package | Plugin name | Status |
|---------|-------------|--------|
| `plugins/eurogirls/` | `eurogirls` | Scaffold — claims `eurogirls_*` export filenames |
| `plugins/eros/` | `eros` | Scaffold — claims `eros_*` export filenames |
| `plugins/custom/` | `custom` | Working template for `*.custom.json` arrays |

See [`plugins/README.md`](../plugins/README.md) for the package layout.

## CLI

```bash
python -m profile_intelligence importers
python -m profile_intelligence import path/to/file.csv
python -m profile_intelligence import path/to/file.xlsx --source crm
python -m profile_intelligence import path/to/profiles.custom.json --plugin custom
```
