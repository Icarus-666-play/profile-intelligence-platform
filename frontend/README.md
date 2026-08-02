# PIP React frontend

Browser → **React** → REST → FastAPI.

## Develop

```bash
# One command (backend :8000 + frontend :5173):
./scripts/start.sh

# Or split terminals:
make backend      # uvicorn …main:app --reload --port 8000
make frontend     # Vite on :5173 (proxies /api → :8000)
```

## Build (commit the output)

```bash
./scripts/build-ui.sh
# or: make build-ui
# or: cd frontend && npm install && npm run build
```

Output: `src/profile_intelligence/web/dist/` (served by FastAPI in production).
