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
- Launch: `./scripts/start.sh` (backend `:8000` + React `:5173`) or `pip-app ui`

## Development

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate

pip install -U pip
pip install -e ".[dev]"

./scripts/start.sh
# Windows: scripts\start.bat
```

This activates the venv, installs missing deps, starts FastAPI, starts the React
dev server, waits for health, and opens the browser.

| URL | Purpose |
|-----|---------|
| http://localhost:5173 | React UI |
| http://127.0.0.1:8000/api/docs | Swagger |
| http://127.0.0.1:8000/api/health | Health |

ASGI wiring (`src/profile_intelligence/api/main.py`):

```python
from profile_intelligence.bootstrap import create_application_context
from profile_intelligence.api.fastapi_app import create_fastapi_app

ctx = create_application_context()
app = create_fastapi_app(ctx)
```

```bash
uvicorn profile_intelligence.api.main:app --reload
pip-app ui
make backend / make frontend / make build-ui / make run
```

## Production

```bash
./scripts/build-ui.sh          # or: cd frontend && npm install && npm run build
uvicorn profile_intelligence.api.main:app
```

Serves the built SPA from `src/profile_intelligence/web/dist/` plus `/api`.

See [docs/BOOTSTRAP.md](docs/BOOTSTRAP.md), [docs/getting-started.md](docs/getting-started.md).

## Project structure

```
├── config/                 # settings.yaml, logging.yaml, scoring.yaml
├── docs/                   # Architecture & guides (incl. BOOTSTRAP.md)
├── frontend/               # React (Vite) SPA
├── scripts/                # start.sh / start.bat / build-ui.*
├── src/profile_intelligence/
│   ├── api/                # FastAPI (main.py ASGI entry)
│   ├── application/        # use cases
│   ├── bootstrap.py        # DI + create_application_context()
│   ├── core/               # config, logging, DI, exceptions
│   ├── domain/             # entities, value_objects, interfaces
│   ├── infrastructure/     # database, importers, excel, search, scoring
│   └── web/dist/           # Built React SPA
└── tests/
```

## Documentation

Product set: [docs/README.md](docs/README.md) (`PRODUCT_VISION` … `ADR/`).

| Document | Description |
|----------|-------------|
| [Bootstrap](docs/BOOTSTRAP.md) | Startup, DI, ApiContext, FastAPI, React |
| [Product Vision](docs/PRODUCT_VISION.md) | Why PIP exists |
| [Getting Started](docs/getting-started.md) | Install, configure, run |
| [Architecture](docs/architecture.md) | Modules and design |
| [Plugin SDK](docs/PLUGIN_SDK.md) | Build importer plugins |
| [Security](docs/SECURITY.md) | Local-first security |

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
pytest
```
