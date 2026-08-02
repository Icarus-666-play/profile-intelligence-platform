"""Official ASGI entry point for Uvicorn.

```
Browser → React → REST API → FastAPI → Application → Repository → SQLite → File Storage
```

Run::

    uvicorn profile_intelligence.api.main:app --reload
"""

from __future__ import annotations

from profile_intelligence.api.fastapi_app import create_fastapi_app
from profile_intelligence.bootstrap import create_application_context

ctx = create_application_context()
app = create_fastapi_app(ctx)

__all__ = ["app", "ctx"]
