"""Local media storage, hashing, thumbnails, and duplicate detection.

```
media/
  hashing.py
  duplicates.py
  thumbnail_service.py
  image_repository.py
```
"""

from __future__ import annotations

from profile_intelligence.infrastructure.media.duplicates import (
    DuplicateImageGroup,
    DuplicateScanResult,
    ImageDuplicateFinder,
)
from profile_intelligence.infrastructure.media.hashing import (
    DEFAULT_ALGORITHM,
    hash_bytes,
    hash_file,
    short_hash,
)
from profile_intelligence.infrastructure.media.image_repository import ImageRepository
from profile_intelligence.infrastructure.media.thumbnail_service import (
    ThumbnailService,
)

__all__ = [
    "DEFAULT_ALGORITHM",
    "DuplicateImageGroup",
    "DuplicateScanResult",
    "ImageDuplicateFinder",
    "ImageRepository",
    "ThumbnailService",
    "hash_bytes",
    "hash_file",
    "short_hash",
]
