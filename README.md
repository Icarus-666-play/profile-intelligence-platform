# Profile Intelligence Platform (PIP)

Local-first desktop application for profile analysis, scoring, Excel reporting, and AI-ready extensibility.

**Windows-first · Python 3.12 · SQLite · Plugin importers · Fully typed**

## Features

### Milestone 0 — Foundation
- Modular package architecture under `src/profile_intelligence/`
- YAML configuration, logging, DI, migrations, repository pattern
- Typed exception hierarchy and quality tooling

### Milestone 1 — Core Profile Pipeline
- Built-in **CSV**, **Excel**, and **Safari `.webarchive`** importer plugins
- External plugin packages under `plugins/` (`eurogirls`, `eros`, `custom`)
- Header-alias extractors → SQLite upsert
- Completeness scoring (0–100)
- Local profile search and compare
- Excel workbook export
- Console dashboard
- CLI: `migrate`, `import`, `list`, `search`, `compare`, `export`, `dashboard`

### Milestone 2 — Dashboard UI
- Local multi-page UI: Dashboard, Search, Import, Compare, Reports, Settings, Plugins, Logs, About
- Launch: `./start.sh` or `pip-app ui` (default `http://127.0.0.1:8765/`)

## Quick start

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate

pip install -U pip
pip install -e .

pip-app migrate
pip-app import samples/profile.webarchive
pip-app list
pip-app search melinda

./start.sh
# uvicorn profile_intelligence.api.main:app --reload
```

See [docs/getting-started.md](docs/getting-started.md) and [docs/milestones.md](docs/milestones.md).

## Project structure

```
├── config/                 # settings.yaml, logging.yaml, scoring.yaml
├── docs/                   # Architecture & guides
├── scripts/                # run_app.py, migrate.py
├── src/profile_intelligence/
│   ├── core/               # config, logging, DI, exceptions
│   ├── database/           # connection, models, repository, migrate, seed
│   ├── domain/             # entities, value_objects, interfaces
│   ├── application/        # use_cases (import, search, compare, …)
│   ├── infrastructure/     # database, importers, excel, search, scoring
│   └── core/               # config, logging, DI, exceptions
└── tests/                  # unit & integration tests
```

## Documentation

Product set: [docs/README.md](docs/README.md) (`PRODUCT_VISION` … `ADR/`).

| Document | Description |
|----------|-------------|
| [Product Vision](docs/PRODUCT_VISION.md) | Why PIP exists |
| [Roadmap](docs/ROADMAP.md) | Milestones & next themes |
| [Getting Started](docs/getting-started.md) | Install, configure, run |
| [Architecture](docs/architecture.md) | Modules and design |
| [Plugin SDK](docs/PLUGIN_SDK.md) | Build importer plugins |
| [Database ERD](docs/DATABASE_ERD.md) | Schema & relationships |
| [Security](docs/SECURITY.md) | Local-first security |
| [Milestones](docs/milestones.md) | Acceptance criteria |

## Development standards

- Python **3.12**
- **PEP 8** via Ruff
- **Type hints** everywhere; `py.typed` shipped; mypy strict
- Dataclasses for config; SQLAlchemy models for persistence
- Logging through `profile_intelligence.core.logging`
- Tests with **pytest**

```bash
ruff check src tests scripts
mypy
pytest --cov=profile_intelligence
```

## License

MIT — see [LICENSE](LICENSE).
