# ADR 0007 — React + FastAPI presentation stack

- **Status:** Accepted
- **Date:** 2026-08-02
- **Supersedes:** [ADR 0004](0004-local-wsgi-dashboard-ui.md) for the default `pip-app ui` surface

## Context

PIP’s lower layers (application use cases, repository ports, SQLite, file storage) are stable. Operators and integrators expect a clear presentation stack:

```
Browser → React → REST API → FastAPI → Application → Repository → SQLite → File Storage
```

The Milestone 2 stdlib WSGI HTML UI (ADR 0004) called use cases in-process and mounted a hand-rolled `/api` WSGI app. That avoided framework cost for M2, but it does not match the target browser/SPA architecture and duplicates HTTP concerns.

## Decision

1. **Default UI** — `pip-app ui` serves a **React** SPA (Vite build under `src/profile_intelligence/web/dist`) over **FastAPI** / uvicorn.
2. **REST** — Wire with `create_api_context()` + `create_fastapi_app(ctx)` (`api/context.py`, `api/fastapi_app.py` / `api/main.py`); routes reuse `profile_intelligence.api.routes` handlers (shared with the legacy WSGI `ApiApp`).
3. **Legacy** — `pip-app ui --legacy-wsgi` keeps the ADR 0004 HTML UI for fallback.
4. **File storage** — `FileStorage` documents/ensures media, inbox, cache, and exports roots beside SQLite.

## Consequences

- Clear Browser → React → FastAPI data path; UI no longer imports use cases directly
- New runtime deps: `fastapi`, `uvicorn`
- React source lives in `frontend/`; commit the production build so `pip-app ui` works without Node at runtime
- OpenAPI available at `/api/docs`
- Loopback-first security posture unchanged (see SECURITY.md)
