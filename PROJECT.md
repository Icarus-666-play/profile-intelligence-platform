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

## Status

Initial repository scaffold is complete:

- Configuration & logging systems
- Application launcher
- SQLite connection layer
- Migration framework
- Empty importer plugin framework
- Exception hierarchy
- Documentation and tests
