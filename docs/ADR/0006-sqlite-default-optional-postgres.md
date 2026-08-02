# ADR 0006 — SQLite default, optional PostgreSQL

- **Status:** Accepted
- **Date:** 2026-08-02

## Context

Desktop installs need a zero-admin database. Some advanced users may prefer PostgreSQL.

## Decision

- Default `database.driver: sqlite` → file under `data/pip.sqlite3`
- Optional `postgresql` driver with URL in config
- Repository port `IProfileRepository` selects adapter in the composition root

PostgreSQL extra: `pip install -e ".[postgres]"`.

## Consequences

- Local-first story stays simple
- Dual-adapter testing burden for profile repository features
- Child/media tables remain SQLite-oriented unless adapters are extended carefully
