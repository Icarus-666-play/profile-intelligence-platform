"""Downloader stage — materialize http(s) / local sources for import."""

from __future__ import annotations

import mimetypes
import re
import shutil
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from profile_intelligence.core.exceptions import ImporterError
from profile_intelligence.core.logging import get_logger
from profile_intelligence.core.types import PathLike
from profile_intelligence.domain.interfaces.plugin_pipeline import DownloadArtifact

logger = get_logger(__name__)

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


class DocumentDownloader:
    """Downloader for profile source documents (files or http/https URLs)."""

    def __init__(
        self,
        download_dir: PathLike,
        *,
        allow_remote: bool = True,
        timeout_seconds: float = 30.0,
        user_agent: str = "ProfileIntelligencePlatform/0.1",
    ) -> None:
        self._download_dir = Path(download_dir)
        self._allow_remote = allow_remote
        self._timeout = timeout_seconds
        self._user_agent = user_agent

    @property
    def download_dir(self) -> Path:
        """Staging directory for downloaded documents."""
        return self._download_dir

    def download(self, source: str | PathLike) -> DownloadArtifact:
        """Materialize *source* under :attr:`download_dir`."""
        text = str(source).strip()
        if not text:
            raise ImporterError("Download source must not be empty")

        self._download_dir.mkdir(parents=True, exist_ok=True)
        parsed = urlparse(text)

        if parsed.scheme in {"http", "https"}:
            if not self._allow_remote:
                raise ImporterError(
                    "Remote download disabled (media.allow_remote_download=false)"
                )
            return self._download_remote(text, parsed.path)

        if parsed.scheme in {"", "file"}:
            local = Path(parsed.path if parsed.scheme == "file" else text)
            return self._copy_local(local.expanduser())

        raise ImporterError(f"Unsupported download scheme: {parsed.scheme!r}")

    def _copy_local(self, source: Path) -> DownloadArtifact:
        if not source.is_file():
            raise ImporterError(f"Source file not found: {source}")
        content_type, _ = mimetypes.guess_type(str(source))
        dest = self._download_dir / source.name
        if source.resolve() != dest.resolve():
            shutil.copy2(source, dest)
            from_cache = False
        else:
            dest = source
            from_cache = True
        logger.info("Downloader local: %s → %s", source, dest)
        return DownloadArtifact(
            path=dest,
            source=str(source),
            content_type=content_type,
            from_cache=from_cache,
        )

    def _download_remote(self, url: str, url_path: str) -> DownloadArtifact:
        suffix = Path(url_path).suffix or ".bin"
        name = _SAFE_NAME.sub("_", Path(url_path).name or "download") or "download"
        if not name.endswith(suffix):
            name = f"{name}{suffix}"
        dest = self._download_dir / name

        request = urllib.request.Request(
            url,
            headers={"User-Agent": self._user_agent},
        )
        try:
            with urllib.request.urlopen(
                request, timeout=self._timeout
            ) as response:
                content = response.read()
                content_type = response.headers.get("Content-Type")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ImporterError(f"Failed to download url: {exc}") from exc

        dest.write_bytes(content)
        logger.info("Downloader remote: %s → %s (%d bytes)", url, dest, len(content))
        return DownloadArtifact(
            path=dest,
            source=url,
            content_type=content_type,
            from_cache=False,
        )


__all__ = ["DocumentDownloader"]
