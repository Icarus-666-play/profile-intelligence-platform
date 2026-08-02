# Product Vision

## Product

**Profile Intelligence Platform (PIP)** is a local-first desktop application for importing, analyzing, scoring, comparing, and reporting on profile data.

## Vision

Give operators a trustworthy, offline-capable workspace to turn heterogeneous profile sources into a structured local database, confidence-scored records, Excel reports, and a clear Dashboard UI — without depending on a cloud backend.

## Problem

Profile data arrives in many file formats (CSV, Excel, Safari `.webarchive`, site-specific HTML/JSON). Teams need to:

- ingest files repeatedly from local folders
- normalize and deduplicate records
- score completeness / confidence
- search and compare profiles
- export Excel and inspect results locally

Cloud-only tools introduce latency, cost, and data residency concerns. PIP keeps the working set on disk (SQLite + local media).

## Goals

| Goal | Meaning |
|------|---------|
| Local-first | SQLite under `data/`; no required network services |
| Windows-first | Primary desktop target; Linux/macOS supported for development |
| Plugin importers | Site/format adapters under `plugins/` without core forks |
| Analysis-ready | Similarity, recommendation, summarization, classification, duplicates |
| AI-ready | Optional `IAIProvider` (Null by default; Local/Remote later) |
| Professional quality | Typed Python 3.12, Ruff, mypy strict, pytest, YAML config |

## Non-goals (current horizon)

- Multi-tenant SaaS / cloud sync
- Live production AI completions (scaffold only until Milestone 3)
- Advanced full-text search engines
- Network-exposed authenticated API server

## Experience pillars

1. **Import** — File → RawDocument → pipeline → SQLite
2. **Understand** — Search, compare, classify, summarize
3. **Operate** — Daily automation, Dashboard UI, Excel reports
4. **Extend** — Importer plugins and future AI providers

## Success looks like

- An operator installs PIP, runs `pip-app migrate`, imports sample files, and finds records via CLI or `pip-app ui`
- Daily inbox processing updates the database, Excel, and dashboard text without manual steps
- A new website source is added as a plugin package without changing core application code

## Related docs

- [PRODUCT_REQUIREMENTS.md](PRODUCT_REQUIREMENTS.md)
- [ROADMAP.md](ROADMAP.md)
- [architecture.md](architecture.md)
