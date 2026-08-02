"""Local JSON REST API for Profile Intelligence Platform.

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
```
"""

from __future__ import annotations

from profile_intelligence.api.app import API_ROUTES, ApiApp, CombinedApp
from profile_intelligence.api.context import ApiContext

__all__ = ["API_ROUTES", "ApiApp", "ApiContext", "CombinedApp"]
