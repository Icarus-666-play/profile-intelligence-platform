"""Content-addressed image storage backed by SQLite metadata."""

from __future__ import annotations

import mimetypes
import shutil
from collections.abc import Sequence
from pathlib import Path

from PIL import Image
from sqlalchemy import select

from profile_intelligence.core.config import AppConfig
from profile_intelligence.core.exceptions import MediaError, RepositoryError
from profile_intelligence.core.logging import get_logger
from profile_intelligence.core.types import PathLike
from profile_intelligence.infrastructure.database.connection import Database
from profile_intelligence.infrastructure.database.models import MediaAsset
from profile_intelligence.infrastructure.database.repository import DatabaseRepository
from profile_intelligence.infrastructure.media.hashing import hash_file
from profile_intelligence.infrastructure.media.thumbnail_service import (
    ThumbnailService,
)

logger = get_logger(__name__)


class ImageRepository(DatabaseRepository[MediaAsset]):
    """Store images on disk and track them in ``media_assets``."""

    def __init__(
        self,
        database: Database,
        config: AppConfig,
        *,
        thumbnail_service: ThumbnailService | None = None,
        create_thumbnails: bool = True,
    ) -> None:
        super().__init__(database)
        self._config = config
        self._thumbnails = thumbnail_service or ThumbnailService(config)
        self._create_thumbnails = create_thumbnails

    @property
    def root_dir(self) -> Path:
        """Directory for canonical image blobs."""
        return self._config.media_dir

    def store(
        self,
        source: PathLike,
        *,
        profile_id: int | None = None,
        create_thumbnail: bool | None = None,
    ) -> MediaAsset:
        """Copy *source* into media storage and upsert metadata.

        Identical content (same hash) reuses the existing asset and updates
        ``profile_id`` when provided.
        """
        source_path = Path(source)
        if not source_path.is_file():
            raise MediaError(f"Image not found: {source_path}")

        self._config.ensure_directories()
        algorithm = self._config.media.hash_algorithm
        digest = hash_file(source_path, algorithm=algorithm)
        extension = source_path.suffix.lower() or ".bin"
        relative_name = f"{digest}{extension}"
        destination = self.root_dir / relative_name

        try:
            if not destination.exists():
                shutil.copy2(source_path, destination)
        except OSError as exc:
            raise MediaError(
                f"Failed to store image at {destination}",
                cause=exc,
            ) from exc

        width, height = self._probe_dimensions(destination)
        content_type, _ = mimetypes.guess_type(str(source_path))
        byte_size = destination.stat().st_size

        should_thumb = (
            self._create_thumbnails
            if create_thumbnail is None
            else create_thumbnail
        )
        thumbnail_path: str | None = None
        if should_thumb:
            try:
                thumb = self._thumbnails.make_thumbnail(destination)
                thumbnail_path = str(thumb)
            except MediaError as exc:
                logger.warning("Thumbnail skipped for %s: %s", destination, exc)

        try:
            with self._database.session() as session:
                existing = session.scalar(
                    select(MediaAsset).where(MediaAsset.content_hash == digest)
                )
                if existing is None:
                    asset = MediaAsset(
                        profile_id=profile_id,
                        content_hash=digest,
                        original_name=source_path.name,
                        content_type=content_type,
                        extension=extension.lstrip(".") or None,
                        byte_size=byte_size,
                        width=width,
                        height=height,
                        storage_path=str(destination),
                        thumbnail_path=thumbnail_path,
                    )
                    session.add(asset)
                    session.flush()
                    session.refresh(asset)
                    session.expunge(asset)
                    logger.info(
                        "Stored media asset id=%s hash=%s",
                        asset.id,
                        digest[:16],
                    )
                    return asset

                if profile_id is not None:
                    existing.profile_id = profile_id
                existing.original_name = source_path.name
                existing.content_type = content_type
                existing.byte_size = byte_size
                existing.width = width
                existing.height = height
                existing.storage_path = str(destination)
                if thumbnail_path is not None:
                    existing.thumbnail_path = thumbnail_path
                session.flush()
                session.refresh(existing)
                session.expunge(existing)
                logger.info(
                    "Reused media asset id=%s hash=%s",
                    existing.id,
                    digest[:16],
                )
                return existing
        except MediaError:
            raise
        except Exception as exc:
            raise RepositoryError(
                "Failed to persist media asset metadata",
                cause=exc,
            ) from exc

    def get_by_id(self, entity_id: int) -> MediaAsset | None:
        """Load a media asset by primary key."""
        try:
            with self._database.session() as session:
                asset = session.get(MediaAsset, entity_id)
                if asset is None:
                    return None
                session.expunge(asset)
                return asset
        except Exception as exc:
            raise RepositoryError(
                f"Failed to load media asset id={entity_id}",
                cause=exc,
            ) from exc

    def list_all(self, *, limit: int = 100, offset: int = 0) -> Sequence[MediaAsset]:
        """List media assets with pagination."""
        if limit < 0 or offset < 0:
            raise RepositoryError("limit and offset must be non-negative")
        try:
            with self._database.session() as session:
                statement = (
                    select(MediaAsset)
                    .order_by(MediaAsset.id)
                    .offset(offset)
                    .limit(limit)
                )
                assets = list(session.scalars(statement).all())
                for asset in assets:
                    session.expunge(asset)
                return assets
        except RepositoryError:
            raise
        except Exception as exc:
            raise RepositoryError("Failed to list media assets", cause=exc) from exc

    def add(self, entity: MediaAsset) -> MediaAsset:
        """Persist a pre-built media asset row (prefer :meth:`store`)."""
        try:
            with self._database.session() as session:
                session.add(entity)
                session.flush()
                session.refresh(entity)
                session.expunge(entity)
                return entity
        except Exception as exc:
            raise RepositoryError("Failed to add media asset", cause=exc) from exc

    def find_by_hash(self, content_hash: str) -> MediaAsset | None:
        """Load a media asset by content hash."""
        try:
            with self._database.session() as session:
                asset = session.scalar(
                    select(MediaAsset).where(
                        MediaAsset.content_hash == content_hash
                    )
                )
                if asset is None:
                    return None
                session.expunge(asset)
                return asset
        except Exception as exc:
            raise RepositoryError(
                "Failed to look up media asset by hash",
                cause=exc,
            ) from exc

    def list_for_profile(self, profile_id: int) -> Sequence[MediaAsset]:
        """Return media assets linked to *profile_id*."""
        try:
            with self._database.session() as session:
                statement = (
                    select(MediaAsset)
                    .where(MediaAsset.profile_id == profile_id)
                    .order_by(MediaAsset.id)
                )
                assets = list(session.scalars(statement).all())
                for asset in assets:
                    session.expunge(asset)
                return assets
        except Exception as exc:
            raise RepositoryError(
                f"Failed to list media for profile_id={profile_id}",
                cause=exc,
            ) from exc

    def delete(self, entity_id: int, *, remove_files: bool = False) -> bool:
        """Delete asset metadata; optionally remove stored files."""
        try:
            with self._database.session() as session:
                asset = session.get(MediaAsset, entity_id)
                if asset is None:
                    return False
                storage_path = Path(asset.storage_path)
                thumbnail_path = (
                    Path(asset.thumbnail_path) if asset.thumbnail_path else None
                )
                session.delete(asset)
            if remove_files:
                for path in (storage_path, thumbnail_path):
                    if path is not None and path.is_file():
                        path.unlink()
            logger.info("Deleted media asset id=%s", entity_id)
            return True
        except Exception as exc:
            raise RepositoryError(
                f"Failed to delete media asset id={entity_id}",
                cause=exc,
            ) from exc

    @staticmethod
    def _probe_dimensions(path: Path) -> tuple[int | None, int | None]:
        try:
            with Image.open(path) as image:
                return int(image.width), int(image.height)
        except Exception:  # noqa: BLE001 - non-image files are allowed
            return None, None
