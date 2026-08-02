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

Programmatic access via `ConfigManager()`:

```python
from profile_intelligence.core.config_manager import ConfigManager

manager = ConfigManager()
manager.load()
print(manager.settings.database_path)
print(manager.get("scoring").weights)
```

Environment overrides:

| Variable | Purpose |
|----------|---------|
| `PIP_CONFIG_PATH` | Absolute path to YAML override |
| `PIP_DATA_DIR` | Override data directory |
| `PIP_LOG_LEVEL` | Override log level (`DEBUG`, `INFO`, …) |
| `PIP_ENVIRONMENT` | Override `app.environment` |

## Primary CLI (`pip-app`)

After install:

```bash
pip install -e .

pip-app migrate
pip-app import profile.webarchive
pip-app list
pip-app search melinda
```

Sample Safari archive: [`samples/profile.webarchive`](../samples/profile.webarchive).

Also supported:

```bash
pip-app import samples/profiles.csv
pip-app compare 1 2
pip-app export
pip-app dashboard
pip-app ui
```

| Command | Purpose |
|---------|---------|
| `migrate` | Apply SQLite migrations |
| `import <path>` | Input → Preview → Validate → Import (`--preview` / `--validate`) |
| `list` | List stored profiles |
| `search <query>` | Local profile search |
| `compare <id_a> <id_b>` | Side-by-side profile diff |
| `export` | Write Excel report under `exports/` |
| `dashboard` | Console dashboard summary |
| `ui` | Local Dashboard UI (Dashboard…About) |

Additional utilities: `seed`, `score`, `importers`.

Equivalent module form: `python -m profile_intelligence <command> …`.

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
