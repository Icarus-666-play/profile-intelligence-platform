"""URL Import operator pipeline stages.

```
URL
 ↓
Downloader
 ↓
Snapshot
 ↓
Parser
 ↓
Extractor
 ↓
Normalizer
 ↓
Validator
 ↓
Preview
 ↓
Import
```
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from profile_intelligence.domain.interfaces.plugin_pipeline import DownloadArtifact

URL_IMPORT_STAGES: tuple[str, ...] = (
    "url",
    "downloader",
    "snapshot",
    "parser",
    "extractor",
    "normalizer",
    "validator",
    "preview",
    "import",
)

URL_IMPORT_STAGE_LABELS: dict[str, str] = {
    "url": "URL",
    "downloader": "Downloader",
    "snapshot": "Snapshot",
    "parser": "Parser",
    "extractor": "Extractor",
    "normalizer": "Normalizer",
    "validator": "Validator",
    "preview": "Preview",
    "import": "Import",
}


@dataclass(frozen=True, slots=True)
class UrlSnapshot:
    """Local snapshot produced after the Downloader stage."""

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
    """Return pipeline stages from ``url`` through *stage* inclusive."""
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
