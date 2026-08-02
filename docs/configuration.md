# Configuration

PIP uses YAML configuration with typed dataclasses (`AppConfig` and nested sections).

## Files

| File | Role |
|------|------|
| `config/default.yaml` | Shipped defaults (required) |
| `config/local.yaml` | Optional developer/machine overrides |
| path in `PIP_CONFIG_PATH` | Optional explicit override |
| `--config` CLI flag | Optional explicit override |

Load order: **defaults → override file → environment variables**.

## Sections

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

### `logging`

- `level`, `console`, `file`, `filename`
- `max_bytes`, `backup_count`
- `format` (mapped to `log_format` in code), `date_format`

### `importers`

- `auto_discover` — discover plugins on startup
- `enabled` — empty list means all plugins; otherwise allow-list of names

### `excel`, `ai`, `search`, `dashboard`

Scaffold settings for upcoming modules. AI remains disabled unless `ai.enabled: true`.

## Programmatic access

```python
from profile_intelligence.core.config import load_config

config = load_config()
print(config.database_path)
config.ensure_directories()
```
