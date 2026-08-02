# Architecture

Profile Intelligence Platform (PIP) is a **local-first**, modular Python desktop application organized in clean-architecture layers. Persistence is SQLite; reporting targets Excel; importers are plugins; AI integration is optional and off by default.

## Package layout

```
src/profile_intelligence/
  domain/
    entities/          # ProfileDraft (+ Rate→…→Availability), ProfileExtractor
    value_objects/     # RawDocument, ImportResult, Rate/Service/Review/Photo/Availability
    events/            # ProfileImported → … → DashboardUpdated
    interfaces/        # ImporterPlugin, repository ports, IEventBus, ICache, IAIProvider
  application/
    pipeline/          # Parser → Normalizer → Validator
    events/            # InMemoryEventBus
    use_cases/         # Import, search, compare, export, dashboard, daily
  infrastructure/
    ai/                # Null AI provider (+ Local/Remote stubs)
    analysis/          # similarity, recommendation, summarization, classification, duplicates
    cache/             # Memory / File / SQLite cache (+ Redis stub)
    database/          # SQLite connection, ORM models, repository, migrate, seed
    importers/         # Registry + built-in plugins (csv, excel, webarchive)
    media/             # download, hash, duplicates, thumbnails, image repository
    excel/             # Excel export adapter
    search/            # SQLite search adapter
    scoring/           # Confidence Score (0-100) via completeness engine
    dashboard/         # Console dashboard adapter / snapshot metrics
    reporting/         # Email report stub (future)
  ui/                  # Milestone 2 Dashboard UI (local WSGI pages)
  core/                # Shared kernel: config, logging, DI, exceptions
  bootstrap.py         # Composition root
  main.py              # CLI / process launcher
```

Dashboard UI (`ui/`) navigation:

```
Profile Intelligence Platform
Dashboard
Search
Import
Compare
Reports
Settings
Plugins
Logs
About
```

Compatibility shims remain at legacy paths (`importers/`, `database/`, `services/`, …) for older imports and external plugins.

Supporting trees:

- `config/` — `settings.yaml`, `logging.yaml`, `scoring.yaml`
- `docs/` — developer documentation
- `scripts/` — convenience launchers
- `tests/` — unit and integration tests
- `plugins/` — external importer packages (`eurogirls`, `newwebsite`, `eros`, `custom`)

## Design principles

| Principle | Implementation |
|-----------|----------------|
| Local-first | SQLite file under `data/`; no required network services |
| Clean architecture | Domain ← Application ← Infrastructure |
| Plugin importers | `ProfileImporter` port + `ImporterRegistry` discovery |
| Repository pattern | `IProfileRepository` → `SQLiteProfileRepository` / `PostgreSQLProfileRepository` |
| Domain events | `ProfileImported` → … → `DashboardUpdated` via `IEventBus` |
| Caching | `ICache` → Memory / File / SQLite (+ Redis stub) |
| Image pipeline | Download → Hash → Duplicate Detection → Thumbnail → Storage |
| Confidence Score | Fixed **0–100** scale (`ConfidenceScorer` / completeness method) |
| AI | `IAIProvider` → Null (default) / Local stub / Remote stub |
| Analysis | similarity / recommendation / summarization / classification / duplicates |
| Dependency injection | Lightweight `Container` in `core.container` |
| Typed | Python 3.12 + `py.typed`, mypy strict |
| Configurable | YAML + env overrides |
| Observable | Structured rotating file + console logging |

## Startup sequence

```
main()
  → build_container()
      → ConfigManager().load()
      → configure_logging()
      → create_database()
      → register use cases / adapters
  → ApplicationService.start()
      → ensure directories
      → run_migrations()
      → ImporterRegistry.discover()
```

## Core data flow

Configured in `config/settings.yaml` and run by `ProcessingChain`:

```
pipeline:
  - parser
  - normalizer
  - validator
  - duplicate_detector
  - scorer
  - repository
```

```
File → RawDocument → ProcessingChain → SQLite
```

Full persist path is `ImportPipeline` (`application/use_cases/`), exposed via `ImportService`:

| Stage | Type | Layer |
|-------|------|-------|
| File | path | — |
| RawDocument | `RawDocument` | domain value object |
| parser | `DocumentParser` + `ProfileImporter` | application/pipeline |
| normalizer | `ProfileNormalizer` → `ProfileDraft` | application/pipeline |
| validator | `ProfileValidator` | application/pipeline |
| duplicate_detector | `DuplicateDetector` | application/pipeline |
| scorer | `ProfileScorer` | application/pipeline |
| repository | `RepositoryStage` → `IProfileRepository` | application/pipeline + infrastructure |
| SQLite | `Database` | infrastructure |

## Image media pipeline

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

Orchestrated by `ImagePipeline` (`application/use_cases/media_pipeline.py`) using
`ImageDownloader`, hashing helpers, `ImageRepository` (content-addressed
dedupe), and `ThumbnailService`. Nightly `extract_images` runs this pipeline
over profile photos and publishes `ImagesExtracted`.

## Cache backends

```
cache/
  SQLite
  Memory
  File
  Redis (future)
```

Select via `cache.backend` in `settings.yaml` (`memory` default). Bound in DI as `ICache`.
Redis raises `CacheError` until implemented.

## Error model

All platform errors inherit from `PipError`. Domain-specific subclasses (`ConfigurationError`, `DatabaseError`, `MigrationError`, `PluginError`, `CacheError`, …) allow precise handling without catching unrelated exceptions.

## Daily automation + workflow events

`DailyPipeline` (`application/use_cases/daily_pipeline.py`) runs:

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

Domain events published during Update / Excel / Dashboard:

```
ProfileImported → ScoreCalculated → ImagesExtracted → ExcelExported → DashboardUpdated
```

New files are detected via `import_file_ledger` (content hash). Email Report is a
stub until the email milestone (`daily.email_enabled`).

CLI: `pip-app daily` (alias: `pip-app nightly`).
Scheduler: `scripts/run_daily.py`.
Config: `daily:` in `config/settings.yaml` (legacy `nightly:` still accepted).

## Extension points

1. **Importers** — subclass `ProfileImporter`, place under `infrastructure/importers/plugins/` or external `plugins/<name>/`
2. **Migrations** — add migration classes in `infrastructure/database/migrate.py`
3. **Use cases** — register additional factories on `Container` in `bootstrap.py`
4. **AI** — `IAIProvider` via `create_ai_provider`; enable with `ai.enabled` and implement Local/Remote adapters (M3)
