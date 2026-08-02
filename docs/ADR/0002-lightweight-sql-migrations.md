# ADR 0002 — Lightweight SQL migrations

- **Status:** Accepted
- **Date:** 2026-08-02

## Context

The app needs reproducible schema changes for SQLite (and optional PostgreSQL) without forcing a heavy migration toolchain on desktop installs.

## Decision

Ship an in-process migration runner (`infrastructure/database/migrate.py`) that:

- tracks versions in `schema_migrations`
- applies ordered Python migration classes (`001`…`005` today)
- runs on `pip-app migrate` and application start

Alembic is not required for M0–M2.

## Consequences

- Simple desktop UX: no separate migration CLI package
- Authors write explicit SQL/DDL in migration classes
- If multi-engineer schema churn grows, revisiting Alembic remains open
