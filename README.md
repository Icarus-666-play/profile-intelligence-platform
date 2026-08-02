# Profile Intelligence Platform (PIP)

Local-first desktop application for profile analysis, scoring, Excel reporting, and AI-ready extensibility.

**Windows-first · Python 3.12 · SQLite · Plugin importers · Fully typed**

## Features

### Milestone 0 — Foundation
- Modular package architecture under `src/profile_intelligence/`
- YAML configuration, logging, DI, migrations, repository pattern
- Typed exception hierarchy and quality tooling

### Milestone 1 — Core Profile Pipeline
- Built-in **CSV** and **Excel** importer plugins
- Header-alias extractors → SQLite upsert
- Completeness scoring (0–100)
- Local profile search
- Excel workbook export
- CLI: `import`, `list`, `search`, `export`, `score`

## Quick start

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate

pip install -U pip
pip install -e ".[dev]"

python -m profile_intelligence migrate
python -m profile_intelligence import samples/profiles.csv
python -m profile_intelligence search Lovelace
python -m profile_intelligence export
pytest
```

See [docs/getting-started.md](docs/getting-started.md) and [docs/milestones.md](docs/milestones.md).

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
| [Milestones](docs/milestones.md) | Roadmap & acceptance |

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
