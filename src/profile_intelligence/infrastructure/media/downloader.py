"""Download / materialize image sources to a local staging directory.

Supports local filesystem paths and ``http`` / ``https`` URLs.
"""

from __future__ import annotations

import mimetypes
import re
import shutil
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from profile_intelligence.core.exceptions import MediaError
from profile_intelligence.core.logging import get_logger
from profile_intelligence.core.types import PathLike

logger = get_logger(__name__)

_DEFAULT_TIMEOUT_SECONDS = 30.0
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(frozen=True, slots=True)
class DownloadResult:
    """Outcome of materializing an image source locally."""

    source: str
    path: Path
    content_type: str | None = None
    from_cache: bool = False


class ImageDownloader:
    """Fetch remote images or copy local files into a downloads directory."""

    def __init__(
        self,
        download_dir: PathLike,
        *,
        allow_remote: bool = True,
        timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
        user_agent: str = "ProfileIntelligencePlatform/0.1",
    ) -> None:
        self._download_dir = Path(download_dir)
        self._allow_remote = allow_remote
        self._timeout = timeout_seconds
        self._user_agent = user_agent

    @property
    def download_dir(self) -> Path:
        """Staging directory for downloaded images."""
        return self._download_dir

    def download(self, source: str | PathLike) -> DownloadResult:
        """Materialize *source* under :attr:`download_dir` and return the path."""
        text = str(source).strip()
        if not text:
            raise MediaError("Image source must not be empty")

        self._download_dir.mkdir(parents=True, exist_ok=True)
        parsed = urlparse(text)

        if parsed.scheme in {"http", "https"}:
            return self._download_remote(text, parsed.path)

        if parsed.scheme in {"", "file"}:
            local = Path(parsed.path if parsed.scheme == "file" else text)
            return self._copy_local(local)

        raise MediaError(f"Unsupported image source scheme: {parsed.scheme!r}")

    def _copy_local(self, source: Path) -> DownloadResult:
        if not source.is_file():
            raise MediaError(f"Image not found: {source}")

        content_type, _ = mimetypes.guess_type(str(source))
        destination = self._unique_destination(
            preferred_name=source.name,
            content_type=content_type,
        )
        try:
            shutil.copy2(source, destination)
        except OSError as exc:
            raise MediaError(
                f"Failed to stage local image {source}",
                cause=exc,
            ) from exc

        logger.debug("Staged local image %s → %s", source, destination)
        return DownloadResult(
            source=str(source),
            path=destination,
            content_type=content_type,
        )

    def _download_remote(self, url: str, url_path: str) -> DownloadResult:
        if not self._allow_remote:
            raise MediaError(
                f"Remote image download disabled (source={url!r})"
            )

        # Schemes restricted to http/https by the caller.
        request = urllib.request.Request(  # noqa: S310
            url,
            headers={"User-Agent": self._user_agent},
            method="GET",
        )
        try:
            with urllib.request.urlopen(  # noqa: S310
                request,
                timeout=self._timeout,
            ) as response:
                payload = response.read()
                content_type = response.headers.get_content_type()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise MediaError(f"Failed to download image: {url}", cause=exc) from exc

        if not payload:
            raise MediaError(f"Downloaded image was empty: {url}")

        preferred = Path(url_path).name or "image"
        destination = self._unique_destination(
            preferred_name=preferred,
            content_type=content_type,
        )
        try:
            destination.write_bytes(payload)
        except OSError as exc:
            raise MediaError(
                f"Failed to write downloaded image to {destination}",
                cause=exc,
            ) from exc

        logger.info(
            "Downloaded image %s → %s (%d bytes)",
            url,
            destination,
            len(payload),
        )
        return DownloadResult(
            source=url,
            path=destination,
            content_type=content_type,
        )

    def _unique_destination(
        self,
        *,
        preferred_name: str,
        content_type: str | None,
    ) -> Path:
        stem = Path(preferred_name).stem or "image"
        stem = _SAFE_NAME.sub("_", stem).strip("._") or "image"
        extension = Path(preferred_name).suffix.lower()
        if not extension and content_type:
            guessed = mimetypes.guess_extension(content_type)
            if guessed:
                extension = guessed
        if not extension:
            extension = ".bin"

        candidate = self._download_dir / f"{stem}{extension}"
        if not candidate.exists():
            return candidate

        counter = 1
        while True:
            candidate = self._download_dir / f"{stem}_{counter}{extension}"
            if not candidate.exists():
                return candidate
            counter += 1
