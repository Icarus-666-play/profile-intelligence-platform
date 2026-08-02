# Profile Intelligence Platform (PIP)

Local-first desktop application for profile analysis, scoring, Excel reporting, and AI-ready extensibility.

**Windows-first · Python 3.12 · SQLite · Plugin importers · Fully typed**

## Features (foundation)

- Modular package architecture under `src/profile_intelligence/`
- YAML configuration with environment overrides
- Structured rotating-file + console logging
- SQLite connection layer (SQLAlchemy 2.x)
- Database migration framework
- Repository pattern
- Lightweight dependency injection container
- Empty, ready-to-extend importer plugin framework
- Typed exception hierarchy
- Unit tests, documentation, and quality tooling (ruff, mypy, pytest)

## Quick start

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate

pip install -U pip
pip install -e ".[dev]"

python -m profile_intelligence --migrate-only
pytest
```

See [docs/getting-started.md](docs/getting-started.md) for full setup details.

## Project structure

```
├── config/                 # YAML defaults
├── docs/                   # Architecture & guides
├── scripts/                # run_app.py, migrate.py
├── src/profile_intelligence/
│   ├── core/               # config, logging, DI, exceptions
│   ├── database/           # SQLite, models, repos, migrations
│   ├── importers/          # plugin framework
│   ├── extractors/         # scaffold
│   ├── services/           # application orchestration
│   ├── scoring/            # scaffold
│   ├── excel/              # scaffold
│   ├── dashboard/          # scaffold
│   ├── search/             # scaffold
│   └── ai/                 # scaffold
└── tests/                  # unit & integration tests
```

## Documentation

| Document | Description |
|----------|-------------|
| [Getting Started](docs/getting-started.md) | Install, configure, run |
| [Architecture](docs/architecture.md) | Modules and design |
| [Configuration](docs/configuration.md) | YAML & env reference |
| [Database](docs/database.md) | SQLite, repos, migrations |
| [Importers](docs/importers.md) | Plugin authoring |

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
