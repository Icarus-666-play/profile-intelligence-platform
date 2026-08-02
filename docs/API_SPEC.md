# API Spec

PIP exposes three operator surfaces:

1. **CLI** — `pip-app`
2. **Local UI** — React SPA via `pip-app ui` (legacy WSGI: `--legacy-wsgi`)
3. **Local JSON REST API** — FastAPI under `/api` (OpenAPI at `/api/docs`)

```
Browser → React → REST API → FastAPI → Application → Repository → SQLite → File Storage
```

Default bind: `127.0.0.1:8765` (loopback). No authentication layer — see [SECURITY.md](SECURITY.md).

## REST API

Served by FastAPI (`create_fastapi_app`). Handlers live in
`profile_intelligence.api.routes` and are shared with the legacy WSGI `ApiApp`.

```
GET    /api/health
GET    /api/auth/status
POST   /api/auth/login
POST   /api/auth/guest
POST   /api/auth/logout
GET    /api/auth/session
POST   /api/import/url
POST   /api/import/url/preview
GET    /api/import/activity
POST   /api/import/files
GET    /api/profiles
GET    /api/profiles/{id}
POST   /api/compare
GET    /api/dashboard
GET    /api/analytics
GET    /api/plugins
POST   /api/plugins/reload
```

Auth supports the React entry flow **Login (optional) → Home → Dashboard**. Default `auth.enabled: false` (guest continue).

Implementation: `src/profile_intelligence/api/` (FastAPI in `fastapi_app.py`).

### Conventions

| Item | Value |
|------|-------|
| Content-Type | `application/json; charset=utf-8` |
| Errors | `{"error": "...", "status": N}` |
| Success | resource JSON objects / lists |

### `POST /api/import/url`

Run the URL import pipeline through Import:

`URL → Downloader → Snapshot → Parser → Extractor → Normalizer → Validator → Preview → Import`

```json
{
  "url": "https://example.com/profiles.csv",
  "urls": ["https://example.com/a.csv", "https://example.com/b.csv"],
  "plugin": "csv",
  "source": "site-a"
}
```

`url` may be multiline (one URL per line). `urls` is an explicit list. Placeholders like `https://...` are ignored.

Requires `media.allow_remote_download: true`.  
Single URL response: import summary (+ `url`, `snapshot`, `pipeline`, `stages_run`, `stage`).  
Multiple URLs: `{ count, imports[], errors[], urls[], pipeline, ok }`.

### `POST /api/import/url/preview`

Same pipeline through Preview (no repository write).

Single URL: preview rows + counts (+ `url`, `downloaded_path`, `snapshot`, `pipeline`, `stages_run`).  
Multiple URLs: `{ count, previews[], errors[], urls[], pipeline, ok }` plus first preview fields for the card.

### `GET /api/import/activity`

Import page panels + pipeline metadata:

```json
{
  "pipeline": ["url", "downloader", "snapshot", "parser", "extractor", "normalizer", "validator", "preview", "import"],
  "stage_labels": { "snapshot": "Snapshot" },
  "recent_urls": [{ "url": "https://…", "at": "…" }],
  "import_queue": [{ "name": "a.csv", "path": "…", "file_size": 123 }],
  "progress": {
    "url": "…",
    "stage": "validator",
    "percent": 75,
    "message": "…",
    "stages_run": ["url", "downloader", "snapshot"],
    "snapshot": { "path": "…", "from_cache": false }
  },
  "errors": [{ "url": "…", "message": "…", "at": "…" }],
  "completed": [{ "url": "…", "created": 1, "success": true, "at": "…" }]
}
```

### `POST /api/import/files`

Import local paths and/or inline base64 files.

```json
{
  "paths": ["/data/inbox/a.csv"],
  "files": [
    {"name": "b.csv", "content_base64": "..."}
  ],
  "plugin": "csv",
  "source": "manual",
  "recursive": false
}
```

Response:

```json
{
  "imports": [ { "created": 1, "updated": 0, "...": "..." } ],
  "errors": [],
  "count": 1
}
```

### `GET /api/profiles`

Query: `limit`, `offset`, optional `q` (search).

```json
{
  "total": 12,
  "limit": 50,
  "offset": 0,
  "items": [
    {
      "id": 1,
      "display_name": "...",
      "score": 80,
      "photo": "https://…",
      "age": "28",
      "country": "Netherlands",
      "languages": ["English", "Italian"],
      "rating": 4.75,
      "average_price": 275.0,
      "average_price_currency": "EUR",
      "imported": "2026-08-02T12:00:00"
    }
  ]
}
```

List/search items include Search-row fields derived from `raw_json` and child tables.

### `GET /api/profiles/{id}`

Single profile object (same field shape), or `404`.

### `POST /api/compare`

```json
{ "left_id": 1, "right_id": 2 }
```

Response includes `fields[]` with `equal` flags plus difference/match counts.

### `GET /api/dashboard`

JSON form of `DashboardService.snapshot()` (totals, by_source, top/incomplete profiles).

### `GET /api/analytics`

Aggregate analysis plus Reports panels. Optional query: `threshold` (duplicate similarity).

```json
{
  "profiles": 12,
  "duplicates": { "scanned": 12, "pairs": 1, "groups": 1, "threshold": 0.75 },
  "classification": { "count": 12, "confidence_bands": {}, "completeness": {} },
  "by_source": [{ "source": "eurogirls", "count": 8 }],
  "countries": [{ "name": "Netherlands", "count": 4 }],
  "average_prices": [{ "label": "1 hour", "average": 300, "currency": "EUR", "count": 5 }],
  "languages": [{ "name": "English", "count": 10 }],
  "services": [{ "name": "GFE", "count": 6 }],
  "duplicate_pairs": [{ "left_id": 1, "right_id": 2, "left_name": "A", "right_name": "B", "score": 0.91 }],
  "monthly_imports": [{ "period": "2026-08", "count": 3 }],
  "import_trend": [{ "period": "2026-08-01", "count": 1 }]
}
```

### `GET /api/plugins`

List discovered importer plugins (`name`, `description`, `supported_extensions`).

### `POST /api/plugins/reload`

Clear registry and rediscover built-ins + `plugins/` directory.

```json
{ "reloaded": 7, "items": [ ... ] }
```

### `GET /api/settings`

Redacted configuration snapshot for Settings sections:

`theme`, `database`, `plugins`, `scoring`, `import_folder`, `playwright`, `backups`, `meta`.

### `GET /api/backups` / `POST /api/backups`

List or create timestamped SQLite copies under `exports/backups/`.

## CLI (`pip-app`)

| Command | Args / flags | Result |
|---------|--------------|--------|
| `migrate` | — | Apply SQL migrations |
| `import PATH` | `--source`, `--plugin`, `--recursive`, `--input` / `--preview` / `--validate` | Input → Preview → Validate → Import |
| `list` | `--limit`, `--offset` | Print profiles |
| `search QUERY` | `--limit` | Search profiles |
| `compare [LEFT] [RIGHT]` | `--sources A B` | Diff profiles or sources |
| `export` | `--output` | Write `.xlsx` |
| `dashboard` | — | Console dashboard text |
| `ui` | `--host`, `--port`, `--no-browser` | Dashboard UI **and** `/api` |
| `daily` / `nightly` | daily flags | Daily automation |
| `analyze …` | subcommands | Analysis toolkit |
| `importers` / `seed` / `score` | — | Utilities |

## Local UI HTTP routes

| Method | Path | Handler |
|--------|------|---------|
| GET | `/`, `/dashboard` | Dashboard |
| GET | `/search?q=` | Search |
| GET/POST | `/import` | Import wizard (Input→Preview→Validate→Import) |
| GET/POST | `/compare` | Compare form / run |
| GET/POST | `/reports` | Reports / export |
| GET | `/settings` | Settings snapshot |
| GET | `/plugins` | Plugin list |
| GET | `/logs` | Log tails |
| GET | `/about` | About |
| GET | `/static/*` | CSS/JS |

## Application service ports (in-process)

| Service | Operations |
|---------|------------|
| `ImportFlow` / `ImportService` | staged + full import |
| `ProfileService` | list / search / export / rescore |
| `CompareService` | compare_ids |
| `DashboardService` | snapshot |
| `AnalysisService` | similarity / duplicates / classify / … |
| `ImporterRegistry` | list / discover / reload |

## Related

- [UI_WIREFRAMES.md](UI_WIREFRAMES.md)
- [IMPORT_PIPELINE.md](IMPORT_PIPELINE.md)
- [SECURITY.md](SECURITY.md)
- ADR: [0004-local-wsgi-dashboard-ui.md](ADR/0004-local-wsgi-dashboard-ui.md)
