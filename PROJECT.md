# Profile Intelligence Platform (PIP)

Production-quality, local-first desktop application for profile analysis.

## Goals

- Local-first
- Python 3.12
- SQLite
- Excel reporting
- Modular architecture
- Plugin-based importers
- AI-ready
- Windows-first
- Professional coding standards
- Fully documented
- Fully typed

## Standards

- PEP 8 (enforced with Ruff)
- Type hints everywhere (`py.typed`, mypy strict)
- Dataclasses for configuration; SQLAlchemy models for persistence
- Logging via centralized configuration
- YAML configuration
- Plugin architecture for importers
- Repository pattern
- Dependency injection where appropriate
- Unit tests (pytest)

## Package layout

```
src/profile_intelligence/
  domain/          # entities, value_objects, interfaces
  application/
    pipeline/      # parser → … → repository stages
    use_cases/
  infrastructure/  # ai, cache, database, importers, excel, media, search, scoring, dashboard
  core/            # config, logging, DI, exceptions
config/ docs/ scripts/ tests/ plugins/
```

AI providers:

```
AI
  Null (default when disabled)
  Local (future)
  Remote (future)
```

Confidence Score:

```
Confidence Score

0-100
```

Cache package (`infrastructure/cache/`):

```
cache/
  SQLite
  Memory
  File
  Redis (future)
```

Media / image pipeline (`infrastructure/media/` + `ImagePipeline`):

```
Image
 ↓
Download
 ↓
Hash
 ↓
Duplicate Detection
 ↓
Thumbnail
 ↓
Storage
```

EuroGirls Sprint 1 (`plugins/eurogirls/`):

```
plugin.py
parser.py
normalizer.py
extractor.py
tests.py
```

NewWebsite plugin (`plugins/newwebsite/`):

```
plugin.py
parser.py
extractor.py
normalizer.py
validator.py
```

## Milestones

See [docs/milestones.md](docs/milestones.md).

| Milestone | Status | Summary |
|-----------|--------|---------|
| **M0 Foundation** | Complete | Scaffold, config, logging, DB, plugin framework |
| **M1 Core Pipeline** | Complete | CSV/Excel import, extract, search, score, Excel export |
| M2 Dashboard UI | Planned | Windows-first desktop presentation layer |
| M3 AI Assist | Planned | Optional local/remote AI adapters |

## Status

Milestones 0 and 1 are complete. Core import pipeline (`config/settings.yaml`):

```
pipeline:
  - parser
  - normalizer
  - validator
  - duplicate_detector
  - scorer
  - repository
```

Daily automation (`pip-app daily` / `scripts/run_daily.py`):

```
Daily
 ↓
Import Folder
 ↓
Detect new files
 ↓
Import
 ↓
Update
 ↓
Generate Excel
 ↓
Create Dashboard
 ↓
Email Report (future)
```

Publishes: `ProfileImported → ScoreCalculated → ImagesExtracted → ExcelExported → DashboardUpdated`.

The local import → search → score → Excel export loop is operational via CLI.
