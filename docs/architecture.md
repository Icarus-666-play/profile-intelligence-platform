# Architecture

Profile Intelligence Platform (PIP) is a **local-first**, modular Python desktop application. Persistence is SQLite; reporting targets Excel; importers are plugins; AI integration is optional and off by default.

## Package layout

```
src/profile_intelligence/
  core/          # config, logging, DI, exceptions
  database/      # SQLAlchemy engine, models, repositories, migrations
  importers/     # plugin interface + registry + built-in plugins
  extractors/    # field/normalization pipelines (scaffold)
  services/      # application/use-case orchestration
  scoring/       # scoring engines (scaffold)
  excel/         # Excel export (scaffold)
  dashboard/     # desktop UI layer (scaffold)
  search/        # local search (scaffold)
  ai/            # AI provider adapters (scaffold)
  bootstrap.py   # composition root
  main.py        # CLI / process launcher
```

Supporting trees:

- `config/` — YAML defaults
- `docs/` — developer documentation
- `scripts/` — convenience launchers
- `tests/` — unit and integration tests

## Design principles

| Principle | Implementation |
|-----------|----------------|
| Local-first | SQLite file under `data/`; no required network services |
| Modular | Domain packages with clear boundaries |
| Plugin importers | `ImporterPlugin` ABC + `ImporterRegistry` discovery |
| Repository pattern | `Repository[T]` / `ProfileRepository` |
| Dependency injection | Lightweight `Container` in `core.container` |
| Typed | Python 3.12 + `py.typed`, mypy strict |
| Configurable | YAML + env overrides |
| Observable | Structured rotating file + console logging |

## Startup sequence

```
main()
  → build_container()
      → load_config()
      → configure_logging()
      → create_database()
      → register services
  → ApplicationService.start()
      → ensure directories
      → MigrationRunner.migrate()
      → ImporterRegistry.discover()
```

## Error model

All platform errors inherit from `PipError`. Domain-specific subclasses (`ConfigurationError`, `DatabaseError`, `MigrationError`, `PluginError`, …) allow precise handling without catching unrelated exceptions.

## Extension points

1. **Importers** — subclass `ImporterPlugin`, place under `importers/plugins/` or external `plugins/`
2. **Migrations** — add `Migration` subclasses in `database/migrations/versions/` and register in `ALL_MIGRATIONS`
3. **Services** — register additional factories on `Container` in `bootstrap.py`
4. **AI** — enable via `ai.enabled` and implement adapters under `ai/`
