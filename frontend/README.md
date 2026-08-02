# PIP React frontend

Browser → **React** → REST → FastAPI.

## Develop

```bash
# terminal 1 — API
make backend
# or: uvicorn profile_intelligence.api.main:app --reload

# terminal 2 — Vite React (proxies /api → :8765)
make frontend
# or: cd frontend && npm run dev
```

## Build (commit the output)

```bash
make build-ui
# or: cd frontend && npm run build
```

Output: `src/profile_intelligence/web/dist/` (served by FastAPI / `make run`).
