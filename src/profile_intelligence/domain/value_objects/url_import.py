"""URL Import operator progress stages.

```
Download
 ↓
Parse
 ↓
Preview
 ↓
Import
 ↓
Finished
```
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from profile_intelligence.domain.interfaces.plugin_pipeline import DownloadArtifact

URL_IMPORT_STAGES: tuple[str, ...] = (
    "download",
    "parse",
    "preview",
    "import",
    "finished",
)

URL_IMPORT_STAGE_LABELS: dict[str, str] = {
    "download": "Download",
    "parse": "Parse",
    "preview": "Preview",
    "import": "Import",
    "finished": "Finished",
}


@dataclass(frozen=True, slots=True)
class UrlSnapshot:
    """Local snapshot produced after the Download stage."""

    path: Path
    source: str
    content_type: str | None = None
    from_cache: bool = False

    @classmethod
    def from_artifact(cls, artifact: DownloadArtifact) -> UrlSnapshot:
        """Build a snapshot from a downloader artifact."""
        return cls(
            path=artifact.path,
            source=artifact.source,
            content_type=artifact.content_type,
            from_cache=artifact.from_cache,
        )

    def to_mapping(self) -> dict[str, object]:
        """Serialize for API / activity payloads."""
        return {
            "path": str(self.path),
            "source": self.source,
            "content_type": self.content_type,
            "from_cache": self.from_cache,
        }


def stage_percent(stage: str) -> int:
    """Return a 0–100 progress percent for *stage* in the URL import chain."""
    try:
        index = URL_IMPORT_STAGES.index(stage)
    except ValueError:
        return 0
    if len(URL_IMPORT_STAGES) <= 1:
        return 100
    return int(round((index / (len(URL_IMPORT_STAGES) - 1)) * 100))


def stages_through(stage: str) -> tuple[str, ...]:
    """Return pipeline stages from ``download`` through *stage* inclusive."""
    try:
        index = URL_IMPORT_STAGES.index(stage)
    except ValueError:
        return ()
    return URL_IMPORT_STAGES[: index + 1]


__all__ = [
    "URL_IMPORT_STAGE_LABELS",
    "URL_IMPORT_STAGES",
    "UrlSnapshot",
    "stage_percent",
    "stages_through",
]
