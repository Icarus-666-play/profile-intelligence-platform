# PIP React frontend

Browser → **React** → REST → FastAPI.

## Develop

```bash
# terminal 1 — API + built SPA (or API-only while iterating)
pip-app ui --no-browser

# terminal 2 — Vite dev server (proxies /api → :8765)
cd frontend
npm install
npm run dev
```

## Build (commit the output)

```bash
cd frontend
npm install
npm run build
```

Output: `src/profile_intelligence/web/dist/` (served by FastAPI).
