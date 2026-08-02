"""Cache backends.

```
cache/
  SQLite
  Memory
  File
  Redis (future)
```
"""

from __future__ import annotations

from profile_intelligence.infrastructure.cache.factory import create_cache
from profile_intelligence.infrastructure.cache.file_cache import FileCache
from profile_intelligence.infrastructure.cache.memory import MemoryCache
from profile_intelligence.infrastructure.cache.redis_cache import RedisCache
from profile_intelligence.infrastructure.cache.sqlite_cache import SQLiteCache

__all__ = [
    "FileCache",
    "MemoryCache",
    "RedisCache",
    "SQLiteCache",
    "create_cache",
]
