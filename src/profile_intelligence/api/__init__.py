"""Local JSON REST API for Profile Intelligence Platform.

```
Browser → React → REST API → FastAPI → Application → Repository → SQLite → Files
```

Endpoints::

```
POST   /api/import/url
POST   /api/import/files
GET    /api/profiles
GET    /api/profiles/{id}
POST   /api/compare
GET    /api/dashboard
GET    /api/analytics
GET    /api/plugins
POST   /api/plugins/reload
GET    /api/health
```
"""

from __future__ import annotations

from profile_intelligence.api.app import API_ROUTES, ApiApp, CombinedApp
from profile_intelligence.api.context import ApiContext
from profile_intelligence.api.fastapi_app import create_fastapi_app
from profile_intelligence.api.server import serve_fastapi

__all__ = [
    "API_ROUTES",
    "ApiApp",
    "ApiContext",
    "CombinedApp",
    "create_fastapi_app",
    "serve_fastapi",
]
