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

## Configuration

Logging is configured from `config/logging.yaml` via `configure_logging()` during application bootstrap.

| Key | Purpose |
|-----|---------|
| `level` | `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL` |
| `console` | Emit to stderr |
| `file` | Emit to rotating file under `logs/` |
| `filename` | Log file name (default `pip.log`) |

## API

- `get_logger(__name__)` — module logger under `profile_intelligence.*`
- `configure_logging(config)` — apply YAML settings
- `reset_logging()` — test helper
