"""Generate and store image thumbnails."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from profile_intelligence.core.config import AppConfig
from profile_intelligence.core.exceptions import MediaError
from profile_intelligence.core.logging import get_logger
from profile_intelligence.core.types import PathLike
from profile_intelligence.infrastructure.media.hashing import hash_file, short_hash

logger = get_logger(__name__)


class ThumbnailService:
    """Create resized thumbnails under the configured media directory."""

    def __init__(self, config: AppConfig) -> None:
        self._config = config

    @property
    def output_dir(self) -> Path:
        """Directory where thumbnails are written."""
        return self._config.thumbnails_dir

    def make_thumbnail(
        self,
        source: PathLike,
        *,
        max_size: int | None = None,
        output_path: PathLike | None = None,
    ) -> Path:
        """Create a thumbnail for *source* and return the output path."""
        source_path = Path(source)
        if not source_path.is_file():
            raise MediaError(f"Image not found: {source_path}")

        size = max_size or self._config.media.thumbnail_max_size
        if size < 1:
            raise MediaError("thumbnail max_size must be >= 1")

        self._config.ensure_directories()
        destination = (
            Path(output_path)
            if output_path is not None
            else self._default_output_path(source_path)
        )
        if not destination.is_absolute():
            destination = (self._config.root_dir / destination).resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)

        fmt = self._config.media.thumbnail_format
        quality = self._config.media.thumbnail_quality

        try:
            with Image.open(source_path) as opened:
                working = (
                    opened.convert("RGB") if fmt in {"JPEG", "JPG"} else opened
                )
                working.thumbnail((size, size))
                save_kwargs: dict[str, object] = {}
                if fmt in {"JPEG", "JPG"}:
                    save_kwargs["quality"] = quality
                    save_kwargs["optimize"] = True
                working.save(destination, format=fmt, **save_kwargs)
        except MediaError:
            raise
        except Exception as exc:
            raise MediaError(
                f"Failed to create thumbnail for {source_path}",
                cause=exc,
            ) from exc

        logger.info(
            "Thumbnail created: source=%s dest=%s size=%d",
            source_path,
            destination,
            size,
        )
        return destination

    def _default_output_path(self, source: Path) -> Path:
        digest = short_hash(
            hash_file(source, algorithm=self._config.media.hash_algorithm)
        )
        extension = self._extension_for_format(self._config.media.thumbnail_format)
        return self.output_dir / f"{digest}{extension}"

    @staticmethod
    def _extension_for_format(fmt: str) -> str:
        mapping = {
            "JPEG": ".jpg",
            "JPG": ".jpg",
            "PNG": ".png",
            "WEBP": ".webp",
            "GIF": ".gif",
        }
        return mapping.get(fmt.upper(), f".{fmt.lower()}")
