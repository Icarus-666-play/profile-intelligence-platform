# API Spec

PIP does **not** expose a public REST/OpenAPI service. The supported surfaces are:

1. **CLI** — `pip-app` (`profile_intelligence.main:main`)
2. **Local UI** — WSGI routes on loopback (`profile_intelligence.ui`)
3. **Internal ports** — domain/application interfaces used by both

## CLI (`pip-app`)

Global flags:

| Flag | Description |
|------|-------------|
| `--version` | Print version |
| `--config PATH` | Merge overlay YAML over `config/settings.yaml` |

### Commands

| Command | Args / flags | Result |
|---------|--------------|--------|
| `migrate` | — | Apply SQL migrations |
| `import PATH` | `--source`, `--plugin`, `--recursive` | Import file/dir → SQLite |
| `list` | `--limit`, `--offset` | Print profiles |
| `search QUERY` | `--limit` | Search profiles |
| `compare [LEFT] [RIGHT]` | `--sources A B` | Diff profiles or sources |
| `export` | `--output` | Write `.xlsx` |
| `dashboard` | — | Console dashboard text |
| `ui` | `--host`, `--port`, `--no-browser` | Serve Dashboard UI |
| `daily` / `nightly` | `--import-dir`, `--excel-output`, `--dashboard-output`, `--no-rescore`, `--recursive`, `--force-all-files` | Daily automation |
| `analyze similarity LEFT RIGHT` | — | Similarity score |
| `analyze recommend ID` | `--limit` | Similar profiles |
| `analyze summarize ID` | — | Profile summary |
| `analyze classify [ID]` | `--all` | Classification |
| `analyze duplicates` | `--threshold` | Near-duplicates |
| `importers` | — | List plugins |
| `seed` | `--only-if-empty` | Demo data |
| `score` | — | Rescore all profiles |

Exit codes: `0` success, `1` domain/import failure, `2` unexpected error.

## Local UI HTTP routes

Server: `wsgiref` via `serve_ui()` — default `127.0.0.1:8765`.

| Method | Path | Handler |
|--------|------|---------|
| GET | `/`, `/dashboard` | Dashboard |
| GET | `/search?q=` | Search |
| GET/POST | `/import` | Import form / run |
| GET/POST | `/compare` | Compare form / run |
| GET/POST | `/reports` | Reports / export |
| GET | `/settings` | Settings snapshot |
| GET | `/plugins` | Plugin list |
| GET | `/logs` | Log tails |
| GET | `/about` | About |
| GET | `/static/styles.css` | CSS |
| GET | `/static/app.js` | JS |

POST bodies: `application/x-www-form-urlencoded`.

There is no JSON REST contract and no API authentication layer.

## Application service ports (in-process)

| Service | Module | Operations |
|---------|--------|------------|
| `ImportService` | `application/use_cases/import_service.py` | `import_path`, `import_directory` |
| `ProfileService` | `application/use_cases/profile_service.py` | `list`, `search`, `export_excel`, `rescore_all` |
| `CompareService` | `application/use_cases/compare_service.py` | `compare_ids` |
| `DashboardService` | `infrastructure/dashboard/service.py` | `snapshot`, `render_text` |
| `AnalysisService` | `infrastructure/analysis/service.py` | similarity / recommend / summarize / classify / duplicates |
| `DailyPipeline` | `application/use_cases/daily_pipeline.py` | `run` |
| `IAIProvider` | `domain/interfaces` + `infrastructure/ai` | optional completions |
| `ICache` | `domain/interfaces` + `infrastructure/cache` | cache backends |
| Repository ports | `domain/interfaces/repositories.py` | profile + children |

## Domain events (internal)

Published on the in-process event bus during workflows:

```
ProfileImported → ScoreCalculated → ImagesExtracted → ExcelExported → DashboardUpdated
```

## Future

A versioned HTTP JSON API is **not** committed. If added later, it should sit beside the UI as an optional adapter over the same application services, not replace them.

## Related

- [UI_WIREFRAMES.md](UI_WIREFRAMES.md)
- [PLUGIN_SDK.md](PLUGIN_SDK.md)
- [IMPORT_PIPELINE.md](IMPORT_PIPELINE.md)
