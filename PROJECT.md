# Profile Intelligence Platform (PIP)

Production-quality, local-first desktop application for profile analysis.

## Goals

- Local-first
- Python 3.12
- SQLite
- Excel reporting
- Modular architecture
- Plugin-based importers
- AI-ready
- Windows-first
- Professional coding standards
- Fully documented
- Fully typed

## Standards

- PEP 8 (enforced with Ruff)
- Type hints everywhere (`py.typed`, mypy strict)
- Dataclasses for configuration; SQLAlchemy models for persistence
- Logging via centralized configuration
- YAML configuration
- Plugin architecture for importers
- Repository pattern
- Dependency injection where appropriate
- Unit tests (pytest)

## Package layout

```
src/profile_intelligence/
  core/ database/ importers/ extractors/ services/
  scoring/ excel/ dashboard/ search/ ai/
config/ docs/ scripts/ tests/ plugins/
```

## Milestones

See [docs/milestones.md](docs/milestones.md).

| Milestone | Status | Summary |
|-----------|--------|---------|
| **M0 Foundation** | Complete | Scaffold, config, logging, DB, plugin framework |
| **M1 Core Pipeline** | Complete | CSV/Excel import, extract, search, score, Excel export |
| M2 Dashboard UI | Planned | Windows-first desktop presentation layer |
| M3 AI Assist | Planned | Optional local/remote AI adapters |

## Status

Milestones 0 and 1 are complete. The local import → extract → persist → search → score → Excel export loop is operational via CLI.
