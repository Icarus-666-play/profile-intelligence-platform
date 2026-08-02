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
| Scoring | Completeness score (0–100) based on populated fields |
| Excel | Workbook export of stored profiles |
| CLI | `import`, `list`, `search`, `export`, `score` subcommands |
| Quality | Unit/integration tests, docs, typed APIs |

### Out of scope (later milestones)

- Desktop dashboard UI
- AI provider integrations
- Advanced fuzzy/full-text search engines
- Network/cloud sync

### Acceptance

1. `pip-app import sample.csv` persists profiles to SQLite
2. `pip-app search <term>` finds matching profiles
3. `pip-app export` writes an `.xlsx` report under `exports/`
4. Profiles receive a completeness score on import
5. Tests and static checks pass
