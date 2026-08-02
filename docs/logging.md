# Logging

PIP uses a centralized logging setup under the `profile_intelligence` namespace.

## Convention

Every module that performs work should declare:

```python
from profile_intelligence.core.logging import get_logger

logger = get_logger(__name__)
```

Then log with the standard levels:

```python
logger.debug("detail...")
logger.info("status...")
logger.warning("recoverable issue...")
logger.error("failure...")
logger.exception("unexpected failure with traceback")
```

## Log files

When file logging is enabled, bootstrap writes rotating files under `logs/`:

| File | Contents |
|------|----------|
| `logs/application.log` | General application activity |
| `logs/import.log` | Importer + import-pipeline activity |
| `logs/errors.log` | `ERROR` and above from all loggers |

Import records are selected by logger name (`profile_intelligence.importers.*` and
`profile_intelligence.services.import_service`). They also appear in `application.log`.

## Configuration

Logging is configured from `config/logging.yaml` via `configure_logging()` during application bootstrap.

| Key | Purpose |
|-----|---------|
| `level` | `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL` |
| `console` | Emit to stderr |
| `file` | Emit to rotating files under `logs/` |
| `files.application` | Application log file name (default `application.log`) |
| `files.import` | Import log file name (default `import.log`) |
| `files.errors` | Errors log file name (default `errors.log`) |
| `max_bytes` / `backup_count` | Rotation settings |
| `format` / `date_format` | Formatter strings |

Legacy `filename` (if present) maps to `files.application`.

## API

- `get_logger(__name__)` — module logger under `profile_intelligence.*`
- `configure_logging(config)` — apply YAML settings
- `reset_logging()` — test helper
