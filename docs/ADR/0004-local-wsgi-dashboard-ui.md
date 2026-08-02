# ADR 0004 — Local WSGI Dashboard UI

- **Status:** Accepted
- **Date:** 2026-08-02

## Context

Milestone 2 requires a Windows-first presentation layer with pages: Dashboard, Search, Import, Compare, Reports, Settings, Plugins, Logs, About. Heavy frameworks (Electron, Qt) add packaging cost; CLI alone is insufficient for operators.

## Decision

Ship a **stdlib WSGI** multi-page UI (`profile_intelligence.ui`) served on loopback (`127.0.0.1:8765` by default) via `pip-app ui`.

Pages call existing application services. The same process also mounts a local JSON REST API under `/api` (`profile_intelligence.api`) for programmatic access — still loopback-first, no separate framework.

## Consequences

- Zero new UI/API framework dependencies for M2
- Works on Windows/Linux/macOS with a browser or HTTP client
- No auth model — bind host must stay loopback on untrusted networks
- A native shell can wrap the same UI/API later without rewriting use cases
