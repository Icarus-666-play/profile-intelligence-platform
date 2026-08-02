# Product Requirements

## Scope

Requirements for Profile Intelligence Platform through Milestone 2 (shipped) and Milestone 3 (planned AI assist).

## Functional requirements

### FR-1 Import

| ID | Requirement | Status |
|----|-------------|--------|
| FR-1.1 | Import profiles from local files (`.csv`, `.xlsx`, `.webarchive`, plugin formats) | Done |
| FR-1.2 | Support directory import with optional recursion | Done |
| FR-1.3 | Run staged pipeline: parser → normalizer → validator → duplicate_detector → scorer → repository | Done |
| FR-1.4 | Allow forcing a plugin via `--plugin` / UI | Done |
| FR-1.5 | Persist profile aggregate children (rates, services, reviews, photos, availability) | Done |

### FR-2 Search & list

| ID | Requirement | Status |
|----|-------------|--------|
| FR-2.1 | List stored profiles with limit/offset | Done |
| FR-2.2 | Search profiles by text query | Done |
| FR-2.3 | Search rows show photo, age, country, languages, rating, average price, imported, and Compare selection | Done |

### FR-3 Compare & analysis

| ID | Requirement | Status |
|----|-------------|--------|
| FR-3.1 | Field-level compare of two profile ids | Done |
| FR-3.2 | Similarity scoring and near-duplicate detection | Done |
| FR-3.3 | Recommendation, summarization, classification | Done |

### FR-4 Scoring & reports

| ID | Requirement | Status |
|----|-------------|--------|
| FR-4.1 | Confidence Score 0–100 on import / rescore | Done |
| FR-4.2 | Excel workbook export under `exports/` | Done |
| FR-4.3 | Console dashboard summary | Done |

### FR-5 Dashboard UI

| ID | Requirement | Status |
|----|-------------|--------|
| FR-5.1 | Local multi-page UI: Dashboard, Search, Import, Compare, Reports, Settings, Plugins, Logs, About | Done |
| FR-5.2 | Bind loopback by default (`127.0.0.1`) | Done |

### FR-6 Daily automation

| ID | Requirement | Status |
|----|-------------|--------|
| FR-6.1 | Import Folder → Detect new files → Import → Update → Excel → Dashboard | Done |
| FR-6.2 | Email report stage (stub / future send) | Partial |

### FR-7 Extensibility

| ID | Requirement | Status |
|----|-------------|--------|
| FR-7.1 | Discover built-in and `plugins/` importers | Done |
| FR-7.2 | Optional AI provider (Null default; Local/Remote planned) | Partial (M3) |

## Non-functional requirements

| ID | Requirement |
|----|-------------|
| NFR-1 | Python 3.12+, fully typed (`mypy --strict`), `py.typed` |
| NFR-2 | Ruff-enforced style; pytest suite green in CI/dev |
| NFR-3 | YAML configuration with local overlays; secrets not committed |
| NFR-4 | SQLite default; optional PostgreSQL driver for profiles |
| NFR-5 | Structured logging to `logs/application.log`, `import.log`, `errors.log` |
| NFR-6 | Local-first: app usable without internet (except optional remote media/AI) |

## Constraints

- Windows-first desktop positioning; no mandatory cloud control plane
- Importer plugins execute as local Python code (trusted install model)
- UI is a local WSGI presentation layer, not a public multi-user web app

## Out of scope

- Multi-user account/auth system (SaaS-style) — optional local Login → Home → Dashboard gate only
- Real-time collaborative editing
- Hosted SaaS deployment

## Traceability

| Area | Spec |
|------|------|
| User journeys | [USER_STORIES.md](USER_STORIES.md) |
| UI | [UI_WIREFRAMES.md](UI_WIREFRAMES.md) |
| Surfaces | [API_SPEC.md](API_SPEC.md) |
| Data | [DATABASE_ERD.md](DATABASE_ERD.md) |
| Plugins | [PLUGIN_SDK.md](PLUGIN_SDK.md) |
| Pipeline | [IMPORT_PIPELINE.md](IMPORT_PIPELINE.md) |
| Security | [SECURITY.md](SECURITY.md) |
| Delivery | [DEPLOYMENT.md](DEPLOYMENT.md) |
| Timeline | [ROADMAP.md](ROADMAP.md) |
