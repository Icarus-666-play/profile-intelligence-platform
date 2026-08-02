# Deployment

PIP deploys as a **local desktop / workstation process**, not a cloud service.

## Supported environments

| Environment | Support |
|-------------|---------|
| Windows 10/11 | Primary |
| Linux | Development / agents |
| macOS | Development |

Runtime: **Python 3.12+**.

## Install

From the repository root:

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

pip install -U pip
pip install -e ".[dev]"          # developers
# pip install -e .               # runtime only
# pip install -e ".[postgres]"   # optional PostgreSQL driver
```

Entry point: `pip-app` → `profile_intelligence.main:main`.

## First-run layout

On start the app ensures:

```
data/          # SQLite + media + inbox
logs/          # rotating logs
exports/       # Excel + dashboard text
plugins/       # external importers
```

```bash
pip-app migrate
pip-app seed --only-if-empty    # optional demo data
pip-app ui                      # Dashboard UI
```

## Configuration

| File | Role |
|------|------|
| `config/settings.yaml` | Shipped defaults |
| `config/logging.yaml` | Logging |
| `config/scoring.yaml` | Confidence weights |
| `config/*.local.yaml` | Gitignored overlays |

Environment overrides: `PIP_CONFIG_PATH`, `PIP_DATA_DIR`, `PIP_LOG_LEVEL`, `PIP_ENVIRONMENT`.

See [configuration.md](configuration.md) and [SECURITY.md](SECURITY.md).

## Day-to-day operations

```bash
pip-app import path\to\file.webarchive --plugin eurogirls
pip-app search "sophia"
pip-app export
pip-app dashboard
pip-app ui --no-browser
pip-app daily
```

### Scheduled Daily run

Windows Task Scheduler / cron can invoke:

```bash
python scripts/run_daily.py
# or
pip-app daily
```

Ensure the task runs as the user that owns `data/` and uses the venv’s `pip-app`.

## Optional PostgreSQL

```yaml
database:
  driver: postgresql
  url: postgresql+psycopg://user:pass@localhost:5432/pip
```

Install extras: `pip install -e ".[postgres]"`.  
SQLite remains the default local-first path.

## Backups

Back up at least:

- `data/pip.sqlite3` (or PostgreSQL dump)
- `data/media/`
- `config/*.local.yaml` (secrets — store securely)
- `exports/` if reports must be retained

Stop writers (`pip-app` processes) before copying SQLite files, or use a filesystem-consistent snapshot.

## Upgrades

1. `git pull` / install new version into the venv
2. `pip install -e .`
3. `pip-app migrate`
4. Run tests if developing: `pytest`

Migrations are additive (`001`–`005` today); review release notes before major jumps.

## What this is not

- Not a Docker/K8s multi-replica web deployment guide
- Not a guide for exposing the UI on the public internet
- Not a SaaS tenancy model

## Related

- [getting-started.md](getting-started.md)
- [SECURITY.md](SECURITY.md)
- [ROADMAP.md](ROADMAP.md)
