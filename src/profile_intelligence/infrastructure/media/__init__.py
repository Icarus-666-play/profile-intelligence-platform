"""Local media storage, hashing, thumbnails, and duplicate detection.

```
Image
 ↓
Download
 ↓
Hash
 ↓
Duplicate Detection
 ↓
Thumbnail
 ↓
Storage
```
"""

from __future__ import annotations

from profile_intelligence.infrastructure.media.downloader import (
    DownloadResult,
    ImageDownloader,
)
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
    "DownloadResult",
    "DuplicateImageGroup",
    "DuplicateScanResult",
    "ImageDownloader",
    "ImageDuplicateFinder",
    "ImageRepository",
    "ThumbnailService",
    "hash_bytes",
    "hash_file",
    "short_hash",
]
