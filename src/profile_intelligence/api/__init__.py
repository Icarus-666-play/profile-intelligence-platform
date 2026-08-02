"""Local JSON REST API for Profile Intelligence Platform.

```
Browser → React → REST API → FastAPI → Application → Repository → SQLite → Files
```

Factory: :func:`profile_intelligence.api.fastapi_app.create_fastapi_app`.  
ASGI entry: ``uvicorn profile_intelligence.api.main:app --reload``.

Endpoints::

```
POST   /api/import/url
POST   /api/import/url/preview
GET    /api/import/activity
POST   /api/import/files
GET    /api/profiles
GET    /api/profiles/{id}
POST   /api/compare
GET    /api/dashboard
GET    /api/daily
POST   /api/daily/run
GET    /api/analytics
GET    /api/plugins
POST   /api/plugins/reload
GET    /api/settings
GET    /api/backups
POST   /api/backups
GET    /api/health
```
"""

from __future__ import annotations

from profile_intelligence.api.app import API_ROUTES, ApiApp, CombinedApp
from profile_intelligence.api.context import ApiContext, create_api_context
from profile_intelligence.api.fastapi_app import create_app, create_fastapi_app
from profile_intelligence.api.server import serve_fastapi

__all__ = [
    "API_ROUTES",
    "ApiApp",
    "ApiContext",
    "CombinedApp",
    "create_api_context",
    "create_app",
    "create_fastapi_app",
    "serve_fastapi",
]
