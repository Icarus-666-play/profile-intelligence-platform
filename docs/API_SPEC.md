# API Spec

PIP exposes three operator surfaces:

1. **CLI** — `pip-app`
2. **Local UI** — HTML pages via `pip-app ui`
3. **Local JSON REST API** — same process, under `/api`

Default bind: `127.0.0.1:8765` (loopback). No authentication layer — see [SECURITY.md](SECURITY.md).

## REST API

Mounted by `pip-app ui` alongside the Dashboard UI.

```
POST   /api/import/url
POST   /api/import/files
GET    /api/profiles
GET    /api/profiles/{id}
POST   /api/compare
GET    /api/dashboard
GET    /api/analytics
GET    /api/plugins
POST   /api/plugins/reload
```

Implementation: `src/profile_intelligence/api/`.

### Conventions

| Item | Value |
|------|-------|
| Content-Type | `application/json; charset=utf-8` |
| Errors | `{"error": "...", "status": N}` |
| Success | resource JSON objects / lists |

### `POST /api/import/url`

Download a remote file and run Import.

```json
{
  "url": "https://example.com/profiles.csv",
  "plugin": "csv",
  "source": "site-a"
}
```

Requires `media.allow_remote_download: true`. Response: import summary (+ `url`).

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
  "items": [ { "id": 1, "display_name": "...", "score": 80 } ]
}
```

### `GET /api/profiles/{id}`

Single profile object, or `404`.

### `POST /api/compare`

```json
{ "left_id": 1, "right_id": 2 }
```

Response includes `fields[]` with `equal` flags plus difference/match counts.

### `GET /api/dashboard`

JSON form of `DashboardService.snapshot()` (totals, by_source, top/incomplete profiles).

### `GET /api/analytics`

Aggregate analysis: score summary, duplicate scan, classification band counts.  
Optional query: `threshold` (duplicate similarity).

### `GET /api/plugins`

List discovered importer plugins (`name`, `description`, `supported_extensions`).

### `POST /api/plugins/reload`

Clear registry and rediscover built-ins + `plugins/` directory.

```json
{ "reloaded": 7, "items": [ ... ] }
```

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
