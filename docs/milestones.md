# Milestones

## Milestone 0 — Foundation (complete)

Repository scaffold: config, logging, SQLite layer, migrations, empty plugin framework, DI, docs, tests.

## Milestone 1 — Core Profile Data Pipeline (complete)

Deliver a complete local import → extract → persist → search → score → Excel export loop.

### Scope

| Area | Deliverable |
|------|-------------|
| Schema | Enriched `profiles` table (email, phone, title, org, location, tags, raw JSON) |
| Importers | Built-in **CSV** and **Excel** (`.xlsx`) plugins returning raw row records |
| Extractors | Header-alias normalization into typed profile drafts |
| Services | Import orchestration, profile listing, search, rescoring |
| Scoring | Confidence Score (0–100) based on populated fields |
| Excel | Workbook export of stored profiles |
| CLI | `import`, `list`, `search`, `export`, `score` subcommands |
| Quality | Unit/integration tests, docs, typed APIs |

### Out of scope (later milestones)

- Live Local/Remote AI completions (scaffold is in place; providers stubbed)
- Advanced fuzzy/full-text search engines
- Network/cloud sync

## Milestone 2 — Dashboard UI (complete)

Local multi-page presentation layer launched with `pip-app ui` (binds `127.0.0.1` by default).

### Navigation

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

### Acceptance

1. `pip-app ui` serves the Dashboard UI locally
2. Each nav page renders against live application services
3. Search / Import / Compare / Reports perform real local operations
4. Tests and static checks pass

## Milestone 3 — AI Assist (planned)

Optional AI assistance behind `IAIProvider`:

```
AI
  Null (default when disabled)
  Local (future)
  Remote (future)
```

Config: `ai.enabled`, `ai.provider`, `ai.model`. Default remains off.

### Acceptance

1. `pip-app migrate` applies schema migrations
2. `pip-app import profile.webarchive` (or `.csv` / `.xlsx`) persists profiles
3. `pip-app list` shows stored profiles
4. `pip-app search melinda` finds matching profiles
5. `pip-app compare <id_a> <id_b>` diffs two profiles
6. `pip-app export` writes an `.xlsx` report under `exports/`
7. `pip-app dashboard` prints a local summary
4. Profiles receive a Confidence Score (0–100) on import
5. Tests and static checks pass
