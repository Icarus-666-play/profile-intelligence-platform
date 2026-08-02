"""ASGI entrypoint for uvicorn.

```
Browser → React → REST API → FastAPI → Application → Repository → SQLite → File Storage
```

Run::

    uvicorn profile_intelligence.api.main:app --reload
"""

from __future__ import annotations

from profile_intelligence.api.context import create_api_context
from profile_intelligence.api.fastapi_app import create_fastapi_app

app = create_fastapi_app(create_api_context())

__all__ = ["app"]
