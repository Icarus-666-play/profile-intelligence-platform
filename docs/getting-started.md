# Getting Started

## Prerequisites

- Python **3.12+**
- Windows recommended (Linux/macOS supported for development)
- Git

## Installation

From the repository root:

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

pip install -U pip
pip install -e ".[dev]"
```

Alternatively:

```bash
pip install -r requirements.txt
pip install -e .
```

## Configuration

Default settings live in [`config/default.yaml`](../config/default.yaml).

Optional local overrides:

1. Copy defaults and edit `config/local.yaml` (gitignored pattern supported), or
2. Set `PIP_CONFIG_PATH` to a YAML file, or
3. Pass `--config path/to/config.yaml` to the launcher

Environment overrides:

| Variable | Purpose |
|----------|---------|
| `PIP_CONFIG_PATH` | Absolute path to YAML override |
| `PIP_DATA_DIR` | Override data directory |
| `PIP_LOG_LEVEL` | Override log level (`DEBUG`, `INFO`, …) |
| `PIP_ENVIRONMENT` | Override `app.environment` |

## Run

```bash
# Module entrypoint
python -m profile_intelligence --migrate-only

# Console script (after editable install)
pip-app --list-importers

# Helper scripts
python scripts/run_app.py
python scripts/migrate.py
```

On first start the application:

1. Creates `data/`, `logs/`, `exports/`, and `plugins/` directories
2. Opens the SQLite database
3. Applies pending migrations
4. Discovers importer plugins

## Tests

```bash
pytest
pytest --cov=profile_intelligence
```

## Quality checks

```bash
ruff check src tests scripts
mypy
```
