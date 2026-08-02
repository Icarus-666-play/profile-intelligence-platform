"""Plugin ingest stage ports.

Canonical site-import chain::

    Downloader
     ↓
    Parser
     ↓
    Extractor
     ↓
    Normalizer
     ↓
    Validator
     ↓
    Importer
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

from profile_intelligence.core.types import PathLike
from profile_intelligence.domain.value_objects.importing import RawRecord

PLUGIN_PIPELINE_STAGES: tuple[str, ...] = (
    "downloader",
    "parser",
    "extractor",
    "normalizer",
    "validator",
    "importer",
)


@dataclass(frozen=True, slots=True)
class DownloadArtifact:
    """Local file produced by the Downloader stage."""

    path: Path
    source: str
    content_type: str | None = None
    from_cache: bool = False


@dataclass(frozen=True, slots=True)
class StageValidationResult:
    """Outcome of the plugin Validator stage."""

    ok: bool
    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)


@runtime_checkable
class IDocumentDownloader(Protocol):
    """Downloader — materialize a remote or local source to disk."""

    def download(self, source: str | PathLike) -> DownloadArtifact:
        """Return a local path for *source*."""


@runtime_checkable
class ISourceParser(Protocol):
    """Parser — decode a local file into a site document."""

    def parse(self, path: Path) -> object:
        """Parse *path* into a site-specific document object."""


@runtime_checkable
class ISourceExtractor(Protocol):
    """Extractor — pull structured profile candidates from a parsed document."""

    def extract_many(self, document: object) -> Sequence[object]:
        """Yield extracted profile objects from *document*."""


@runtime_checkable
class ISourceNormalizer(Protocol):
    """Normalizer — map an extracted object onto a platform RawRecord."""

    def normalize(self, extracted: object, document: object | None = None) -> RawRecord:
        """Return one raw record mapping."""


@runtime_checkable
class ISourceValidator(Protocol):
    """Validator — accept or reject a normalized (or extracted) profile."""

    def validate(
        self,
        record: RawRecord,
        *,
        extracted: object | None = None,
    ) -> StageValidationResult:
        """Return whether *record* may proceed to the Importer outcome."""


__all__ = [
    "PLUGIN_PIPELINE_STAGES",
    "DownloadArtifact",
    "IDocumentDownloader",
    "ISourceExtractor",
    "ISourceNormalizer",
    "ISourceParser",
    "ISourceValidator",
    "StageValidationResult",
]
