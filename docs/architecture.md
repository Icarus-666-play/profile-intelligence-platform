# Architecture

Profile Intelligence Platform (PIP) is a **local-first**, modular Python desktop application organized in clean-architecture layers. Persistence is SQLite; reporting targets Excel; importers are plugins; AI integration is optional and off by default.

## Package layout

```
src/profile_intelligence/
  domain/
    entities/          # ProfileDraft, ProfileExtractor
    value_objects/     # RawDocument, ImportResult, …
    interfaces/        # ImporterPlugin, ProfileImporter, Repository ports
  application/
    pipeline/          # Parser → Normalizer → Validator
    use_cases/         # Import, search, compare, export, dashboard
  infrastructure/
    database/          # SQLite connection, ORM models, repository, migrate, seed
    importers/         # Registry + built-in plugins (csv, excel, webarchive)
    media/             # hashing, duplicates, thumbnails, image repository
    excel/             # Excel export adapter
    search/            # SQLite search adapter
    scoring/           # Completeness scorer
    dashboard/         # Console dashboard adapter
  core/                # Shared kernel: config, logging, DI, exceptions
  bootstrap.py         # Composition root
  main.py              # CLI / process launcher
```

Compatibility shims remain at legacy paths (`importers/`, `database/`, `services/`, …) for older imports and external plugins.

Supporting trees:

- `config/` — `settings.yaml`, `logging.yaml`, `scoring.yaml`
- `docs/` — developer documentation
- `scripts/` — convenience launchers
- `tests/` — unit and integration tests
- `plugins/` — external importer packages (`eurogirls`, `eros`, `custom`)

## Design principles

| Principle | Implementation |
|-----------|----------------|
| Local-first | SQLite file under `data/`; no required network services |
| Clean architecture | Domain ← Application ← Infrastructure |
| Plugin importers | `ProfileImporter` port + `ImporterRegistry` discovery |
| Repository pattern | Domain `Repository` port / infrastructure `ProfileRepository` |
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
| repository | `RepositoryStage` → `ProfileRepository` | application/pipeline + infrastructure |
| SQLite | `Database` | infrastructure |

## Error model

All platform errors inherit from `PipError`. Domain-specific subclasses (`ConfigurationError`, `DatabaseError`, `MigrationError`, `PluginError`, …) allow precise handling without catching unrelated exceptions.

## Extension points

1. **Importers** — subclass `ProfileImporter`, place under `infrastructure/importers/plugins/` or external `plugins/<name>/`
2. **Migrations** — add migration classes in `infrastructure/database/migrate.py`
3. **Use cases** — register additional factories on `Container` in `bootstrap.py`
4. **AI** — enable via `ai.enabled` and implement adapters later under infrastructure
