# Configuration

PIP uses split YAML configuration with typed dataclasses (`AppConfig` and nested sections).

## Files

| File | Role |
|------|------|
| `config/settings.yaml` | App, paths, database, importers, excel, ai, search, dashboard |
| `config/logging.yaml` | Logging options |
| `config/scoring.yaml` | Completeness scoring method/weights |
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

- `echo_sql` — SQLAlchemy engine echo
- `timeout_seconds` — SQLite busy timeout
- `check_same_thread` — sqlite3 connect arg
- `foreign_keys` — enable `PRAGMA foreign_keys=ON`

### `importers`

- `auto_discover` — discover plugins on startup
- `enabled` — empty list means all plugins; otherwise allow-list of names

### `excel`, `ai`, `search`, `dashboard`

Scaffold settings for upcoming modules. AI remains disabled unless `ai.enabled: true`.

## `logging.yaml`

Flat file (not nested under a `logging:` key):

- `level`, `console`, `file`
- `files.application` → `logs/application.log`
- `files.import` → `logs/import.log`
- `files.errors` → `logs/errors.log`
- `max_bytes`, `backup_count`
- `format` (mapped to `log_format` in code), `date_format`

Legacy `filename` maps to `files.application` when `files` is omitted.

## `scoring.yaml`

- `method` — currently `completeness`
- `max_score` — upper bound (default 100)
- `weights` — field → integer weight map

Weights are applied by `CompletenessScorer` at runtime.

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
