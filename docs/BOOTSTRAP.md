# Bootstrap & startup

How Profile Intelligence Platform wires dependency injection and starts the
presentation stack.

## Startup sequence

```
./scripts/start.sh
        │
        ├─ activate .venv (if present)
        ├─ verify Python ≥ 3.12
        ├─ pip install -e ".[dev]" when imports missing
        │
        ├─ uvicorn profile_intelligence.api.main:app --reload
        │         │
        │         ├─ create_application_context()   # bootstrap.py
        │         │         ├─ build_container()
        │         │         ├─ ApplicationService.start()
        │         │         │     (migrate + discover plugins)
        │         │         └─ ApiContext(…)
        │         └─ create_fastapi_app(ctx)         # fastapi_app.py
        │
        ├─ wait for GET /api/health → {"status": "ok", …}
        ├─ npm run dev (frontend/) → http://localhost:5173
        └─ open browser
```

Production / API-only:

```bash
cd frontend && npm run build          # or ./scripts/build-ui.sh
uvicorn profile_intelligence.api.main:app
```

`pip-app ui` uses the same `create_application_context()` + `create_fastapi_app()`
path via `serve_fastapi()` (default port `8765` for the CLI).

## Dependency injection

`build_container()` in `src/profile_intelligence/bootstrap.py` is the composition
root. It loads YAML config, configures logging, and registers:

- infrastructure adapters (database, importers, search, excel, …)
- application use cases (import, profiles, compare, daily, …)
- ports (`IProfileRepository`, `IEventBus`, …)

Nothing in domain / application imports FastAPI.

## ApiContext

`ApiContext` (`api/context.py`) is a typed bag of services for REST handlers.
It is **constructed only** by:

```python
from profile_intelligence.bootstrap import create_application_context

ctx = create_application_context()
```

`create_api_context()` remains a thin alias that calls
`create_application_context()` (no duplicated wiring).

## FastAPI

Factory:

```python
from profile_intelligence.api.fastapi_app import create_fastapi_app

app = create_fastapi_app(ctx)
```

Official ASGI module (`api/main.py`):

```python
from profile_intelligence.api.fastapi_app import create_fastapi_app
from profile_intelligence.bootstrap import create_application_context

ctx = create_application_context()
app = create_fastapi_app(ctx)
```

Handlers live in `api/routes.py` and are shared with the legacy WSGI `ApiApp`.

Stack:

```
Browser → React → REST API → FastAPI → Application → Repository → SQLite → File Storage
```

## React

| Mode | Command | URL |
|------|---------|-----|
| Dev | `make frontend` / `npm run dev` | `http://localhost:5173` (proxies `/api` → `:8000`) |
| Prod build | `./scripts/build-ui.sh` | assets under `src/profile_intelligence/web/dist/` served by FastAPI |

`./scripts/start.sh` starts Vite when `frontend/package.json` exists; otherwise
the backend serves the built SPA (if present) and `/api`.

## Health check

```http
GET /api/health
```

```json
{ "status": "ok", "stack": "fastapi" }
```

OpenAPI / Swagger UI: `http://127.0.0.1:8000/api/docs`.
