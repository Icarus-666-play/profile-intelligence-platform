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

Shipped config files:

- [`config/settings.yaml`](../config/settings.yaml)
- [`config/logging.yaml`](../config/logging.yaml)
- [`config/scoring.yaml`](../config/scoring.yaml)

Optional local overlays (gitignored):

```bash
cp config/settings.local.yaml.example config/settings.local.yaml
cp config/logging.local.yaml.example config/logging.local.yaml
cp config/scoring.local.yaml.example config/scoring.local.yaml
```

Or set `PIP_CONFIG_PATH` / pass `--config` for a settings merge override.

Environment overrides:

| Variable | Purpose |
|----------|---------|
| `PIP_CONFIG_PATH` | Absolute path to YAML override |
| `PIP_DATA_DIR` | Override data directory |
| `PIP_LOG_LEVEL` | Override log level (`DEBUG`, `INFO`, …) |
| `PIP_ENVIRONMENT` | Override `app.environment` |

## Milestone 1 workflows

```bash
# Apply migrations
python -m profile_intelligence migrate

# Load built-in demo profiles
python -m profile_intelligence seed

# List importer plugins (csv, excel)
python -m profile_intelligence importers

# Import sample profiles
python -m profile_intelligence import samples/profiles.csv

# List / search
python -m profile_intelligence list
python -m profile_intelligence search Lovelace

# Export Excel report (writes exports/profiles.xlsx)
python -m profile_intelligence export

# Recompute completeness scores
python -m profile_intelligence score
```

Console script after editable install:

```bash
pip-app import samples/profiles.csv
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
