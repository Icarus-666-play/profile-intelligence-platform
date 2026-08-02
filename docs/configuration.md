# Configuration

PIP uses split YAML configuration with typed dataclasses (`AppConfig` and nested sections).

## Files

| File | Role |
|------|------|
| `config/settings.yaml` | App, paths, database, importers, excel, ai, search, dashboard, media, cache, daily, pipeline |
| `config/logging.yaml` | Logging options |
| `config/scoring.yaml` | Confidence Score (0–100) method/weights |
| `config/*.local.yaml` | Optional machine-local overlays (gitignored) |
| path in `PIP_CONFIG_PATH` / `--config` | Optional settings override merge |

Load order per domain: **shipped file → `*.local.yaml` → settings override path → environment variables**.

## `settings.yaml`

### `app`

- `name`, `short_name`, `version`, `environment`

### `paths`

Relative paths resolve against the repository / install root.

- `data_dir`
- `database_file`
- `logs_dir`
- `exports_dir`
- `plugins_dir`

### `database`

- `driver` — `sqlite` (default) or `postgresql`
- `url` — SQLAlchemy URL (required for PostgreSQL, e.g. `postgresql+psycopg://…`)
- `echo_sql` — SQLAlchemy engine echo
- `timeout_seconds` — SQLite busy timeout
- `check_same_thread` — sqlite3 connect arg
- `foreign_keys` — enable `PRAGMA foreign_keys=ON` (SQLite)

Profile repository adapter is selected by `driver`:
`SQLiteProfileRepository` or `PostgreSQLProfileRepository`.

### `importers`

- `auto_discover` — discover plugins on startup
- `enabled` — empty list means all plugins; otherwise allow-list of names

### `excel`, `search`, `dashboard`

Scaffold settings for upcoming modules.

### `ai`

```
AI
  Null (default when disabled)
  Local (future)
  Remote (future)
```

- `enabled` — master switch (default `false` → `NullAIProvider`)
- `provider` — `null` \| `local`/`ollama` \| `remote`/`openai`
- `model` — model id (reserved until M3)
- `base_url` — local/remote endpoint (reserved)
- `api_key` — remote credential (reserved)

Local/Remote raise `AIError` until the M3 AI Assist milestone.

### `media`

Image pipeline: **Download → Hash → Duplicate Detection → Thumbnail → Storage**.

- `root_dir` — content-addressed image blob storage
- `thumbnails_dir` — generated thumbnails
- `downloads_dir` — staging directory for the Download stage
- `hash_algorithm` — default `sha256`
- `thumbnail_max_size`, `thumbnail_format`, `thumbnail_quality`
- `allow_remote_download` — permit `http`/`https` fetches (default `true`)
- `download_timeout_seconds` — remote download timeout

### `cache`

```
cache/
  SQLite
  Memory
  File
  Redis (future)
```

- `backend` — `memory` (default) \| `file` \| `sqlite` \| `redis` (future)
- `ttl_seconds` — default entry TTL (`0` / `null` = no expiry)
- `file_dir` — directory for the `file` backend
- `sqlite_file` — path for the `sqlite` backend
- `redis_url` — reserved for the future Redis backend

### `daily`

```
Daily → Import Folder → Detect new files → Import → Update →
Generate Excel → Create Dashboard → Email Report (future)
```

- `import_dir` — import folder / inbox (default `data/inbox`)
- `excel_path` — Daily Excel report path
- `dashboard_path` — Daily dashboard export path
- `rescore` — recompute Confidence Scores during Update
- `recursive` — recurse import folder
- `email_enabled` — reserved for Email Report (default `false`)
- `email_to` — reserved recipient

Legacy `nightly:` keys are still accepted and merged under `daily`.

## `logging.yaml`

Flat file (not nested under a `logging:` key):

- `level`, `console`, `file`
- `files.application` → `logs/application.log`
- `files.import` → `logs/import.log`
- `files.errors` → `logs/errors.log`
- `max_bytes`, `backup_count`
- `format` (mapped to `log_format` in code), `date_format`

Legacy `filename` maps to `files.application` when `files` is omitted.

## `scoring.yaml` — Confidence Score (0–100)

```
Confidence Score

0-100
```

- `method` — `completeness` (weighted field presence)
- `max_score` — engine upper bound before normalization (default 100)
- `weights` — field → integer weight map

`ConfidenceScorer` normalizes the engine total onto the fixed **0–100** scale.
Stored on profiles as `score` / exported as `confidence_score`.

## Local overrides

```bash
cp config/settings.local.yaml.example config/settings.local.yaml
cp config/logging.local.yaml.example config/logging.local.yaml
cp config/scoring.local.yaml.example config/scoring.local.yaml
```

## Environment variables

| Variable | Purpose |
|----------|---------|
| `PIP_CONFIG_PATH` | YAML merged into settings |
| `PIP_DATA_DIR` | Override data directory |
| `PIP_LOG_LEVEL` | Override log level |
| `PIP_ENVIRONMENT` | Override `app.environment` |

## Programmatic access

Prefer :class:`ConfigManager` (`core/config_manager.py`):

```python
from profile_intelligence.core.config_manager import ConfigManager

manager = ConfigManager()
config = manager.load()
print(manager.settings.database_path)
print(manager.get("scoring").weights)
manager.ensure_directories()

# Reload from disk after editing YAML
manager.reload()
```

Convenience wrapper (still supported):

```python
from profile_intelligence.core.config_manager import load_config

config = load_config()
```
