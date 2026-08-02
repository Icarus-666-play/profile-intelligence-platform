"""Image media processing pipeline.

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

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from profile_intelligence.core.config import AppConfig
from profile_intelligence.core.exceptions import MediaError
from profile_intelligence.core.logging import get_logger
from profile_intelligence.core.types import PathLike
from profile_intelligence.domain.interfaces.repositories import IPhotoRepository
from profile_intelligence.domain.value_objects.profile_children import Photo
from profile_intelligence.infrastructure.media.downloader import ImageDownloader
from profile_intelligence.infrastructure.media.hashing import hash_file
from profile_intelligence.infrastructure.media.image_repository import ImageRepository
from profile_intelligence.infrastructure.media.thumbnail_service import ThumbnailService

logger = get_logger(__name__)

DEFAULT_IMAGE_PIPELINE_STAGES: tuple[str, ...] = (
    "download",
    "hash",
    "duplicate_detection",
    "thumbnail",
    "storage",
)


@dataclass(frozen=True, slots=True)
class ImageSource:
    """An image to run through the media pipeline."""

    uri: str
    profile_id: int | None = None
    role: str = "gallery"
    known_hash: str | None = None
    content_type: str | None = None


@dataclass(frozen=True, slots=True)
class ImagePipelineItemResult:
    """Outcome for a single image source."""

    source: str
    stages_run: tuple[str, ...] = field(default_factory=tuple)
    local_path: str | None = None
    content_hash: str | None = None
    is_duplicate: bool = False
    thumbnail_path: str | None = None
    asset_id: int | None = None
    storage_path: str | None = None
    skipped: bool = False
    errors: tuple[str, ...] = field(default_factory=tuple)

    @property
    def success(self) -> bool:
        """True when the image was stored or reused without hard errors."""
        return self.asset_id is not None and not self.errors


@dataclass(frozen=True, slots=True)
class ImagePipelineResult:
    """Aggregate outcome of an image pipeline run."""

    items: tuple[ImagePipelineItemResult, ...] = field(default_factory=tuple)
    stages: tuple[str, ...] = DEFAULT_IMAGE_PIPELINE_STAGES

    @property
    def processed(self) -> int:
        """Images that ended with a stored media asset."""
        return sum(1 for item in self.items if item.asset_id is not None)

    @property
    def stored_new(self) -> int:
        """Images stored that were not duplicates."""
        return sum(
            1
            for item in self.items
            if item.asset_id is not None and not item.is_duplicate
        )

    @property
    def duplicates(self) -> int:
        """Images that matched an existing content hash."""
        return sum(1 for item in self.items if item.is_duplicate)

    @property
    def failed(self) -> int:
        """Images that failed with errors."""
        return sum(1 for item in self.items if item.errors)

    @property
    def success(self) -> bool:
        """True when every item succeeded or was intentionally skipped."""
        return self.failed == 0


class ImagePipeline:
    """Orchestrates Image → Download → Hash → Duplicate → Thumbnail → Storage."""

    def __init__(
        self,
        config: AppConfig,
        image_repository: ImageRepository,
        *,
        downloader: ImageDownloader | None = None,
        thumbnail_service: ThumbnailService | None = None,
        photo_repository: IPhotoRepository | None = None,
        stages: Sequence[str] | None = None,
    ) -> None:
        self._config = config
        self._images = image_repository
        self._photos = photo_repository
        self._thumbnails = thumbnail_service or ThumbnailService(config)
        self._downloader = downloader or ImageDownloader(
            config.media_downloads_dir,
            allow_remote=config.media.allow_remote_download,
            timeout_seconds=config.media.download_timeout_seconds,
        )
        self._stages = (
            tuple(stages) if stages is not None else DEFAULT_IMAGE_PIPELINE_STAGES
        )

    @property
    def stages(self) -> tuple[str, ...]:
        """Configured pipeline stage names."""
        return self._stages

    def process(
        self,
        source: ImageSource | str | PathLike,
    ) -> ImagePipelineItemResult:
        """Run one image through the full pipeline."""
        item = (
            source
            if isinstance(source, ImageSource)
            else ImageSource(uri=str(source))
        )
        return self._process_one(item)

    def process_many(
        self,
        sources: Sequence[ImageSource | str | PathLike],
    ) -> ImagePipelineResult:
        """Run many images through the pipeline."""
        items = [self.process(source) for source in sources]
        result = ImagePipelineResult(items=tuple(items), stages=self._stages)
        logger.info(
            "Image pipeline batch: total=%d stored=%d new=%d duplicates=%d failed=%d",
            len(result.items),
            result.processed,
            result.stored_new,
            result.duplicates,
            result.failed,
        )
        return result

    def process_profiles(
        self,
        profile_ids: Sequence[int],
    ) -> ImagePipelineResult:
        """Download and store photos registered on the given profiles."""
        if self._photos is None:
            raise MediaError(
                "ImagePipeline.process_profiles requires a photo repository"
            )

        items: list[ImagePipelineItemResult] = []
        for profile_id in profile_ids:
            photos = list(self._photos.list_for_profile(int(profile_id)))
            if not photos:
                continue

            updated: list[Photo] = []
            changed = False
            for photo in photos:
                item = self._process_one(
                    ImageSource(
                        uri=photo.original_url,
                        profile_id=int(profile_id),
                        role=photo.role,
                        known_hash=photo.sha256,
                        content_type=photo.content_type,
                    )
                )
                items.append(item)
                if item.content_hash and item.content_hash != photo.sha256:
                    updated.append(
                        Photo(
                            original_url=photo.original_url,
                            sha256=item.content_hash,
                            role=photo.role,
                            content_type=photo.content_type,
                        )
                    )
                    changed = True
                else:
                    updated.append(photo)

            if changed:
                self._photos.replace_for_profile(int(profile_id), updated)

        batch = ImagePipelineResult(items=tuple(items), stages=self._stages)
        logger.info(
            "Image pipeline profiles: profiles=%d photos=%d stored=%d failed=%d",
            len(profile_ids),
            len(batch.items),
            batch.processed,
            batch.failed,
        )
        return batch

    def _process_one(self, source: ImageSource) -> ImagePipelineItemResult:
        stages_run: list[str] = []
        errors: list[str] = []
        local_path: Path | None = None
        content_hash: str | None = source.known_hash
        is_duplicate = False
        thumbnail_path: Path | None = None
        asset_id: int | None = None
        storage_path: str | None = None

        try:
            self._config.ensure_directories()

            # Known hash already in storage → duplicate short-circuit.
            if source.known_hash:
                existing = self._images.find_by_hash(source.known_hash)
                if existing is not None:
                    asset = self._images.store(
                        existing.storage_path,
                        profile_id=source.profile_id,
                        create_thumbnail=False,
                        thumbnail_path=existing.thumbnail_path,
                    )
                    return ImagePipelineItemResult(
                        source=source.uri,
                        stages_run=("duplicate_detection", "storage"),
                        local_path=existing.storage_path,
                        content_hash=existing.content_hash,
                        is_duplicate=True,
                        thumbnail_path=existing.thumbnail_path,
                        asset_id=asset.id,
                        storage_path=asset.storage_path,
                    )

            for stage in self._stages:
                if stage == "download":
                    downloaded = self._downloader.download(source.uri)
                    local_path = downloaded.path
                    stages_run.append(stage)
                elif stage == "hash":
                    if local_path is None:
                        raise MediaError("Hash stage requires a downloaded image")
                    content_hash = hash_file(
                        local_path,
                        algorithm=self._config.media.hash_algorithm,
                    )
                    stages_run.append(stage)
                elif stage == "duplicate_detection":
                    if content_hash is None:
                        raise MediaError(
                            "Duplicate detection requires a content hash"
                        )
                    existing = self._images.find_by_hash(content_hash)
                    is_duplicate = existing is not None
                    if existing is not None and existing.thumbnail_path:
                        thumbnail_path = Path(existing.thumbnail_path)
                    stages_run.append(stage)
                elif stage == "thumbnail":
                    if local_path is None:
                        raise MediaError(
                            "Thumbnail stage requires a downloaded image"
                        )
                    if not (is_duplicate and thumbnail_path is not None):
                        thumbnail_path = self._thumbnails.make_thumbnail(local_path)
                    stages_run.append(stage)
                elif stage == "storage":
                    if local_path is None:
                        raise MediaError(
                            "Storage stage requires a downloaded image"
                        )
                    asset = self._images.store(
                        local_path,
                        profile_id=source.profile_id,
                        create_thumbnail=False,
                        thumbnail_path=thumbnail_path,
                    )
                    asset_id = asset.id
                    storage_path = asset.storage_path
                    content_hash = asset.content_hash
                    if asset.thumbnail_path:
                        thumbnail_path = Path(asset.thumbnail_path)
                    stages_run.append(stage)
                else:
                    raise MediaError(f"Unknown image pipeline stage: {stage!r}")

        except Exception as exc:  # noqa: BLE001 - capture per-item failures
            message = f"{source.uri}: {exc}"
            errors.append(message)
            logger.warning("Image pipeline failed for %s: %s", source.uri, exc)

        return ImagePipelineItemResult(
            source=source.uri,
            stages_run=tuple(stages_run),
            local_path=str(local_path) if local_path is not None else None,
            content_hash=content_hash,
            is_duplicate=is_duplicate,
            thumbnail_path=(
                str(thumbnail_path) if thumbnail_path is not None else None
            ),
            asset_id=asset_id,
            storage_path=storage_path,
            skipped=False,
            errors=tuple(errors),
        )
