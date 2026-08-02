"""Plugin ingest orchestrator.

```
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
```

Platform persistence still continues afterward via::

    parser → normalizer → validator → duplicate_detector → scorer → repository
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from profile_intelligence.core.logging import get_logger
from profile_intelligence.core.types import PathLike
from profile_intelligence.domain.interfaces.plugin_pipeline import (
    PLUGIN_PIPELINE_STAGES,
    IDocumentDownloader,
    ISourceExtractor,
    ISourceNormalizer,
    ISourceParser,
    ISourceValidator,
    StageValidationResult,
)
from profile_intelligence.domain.value_objects.importing import ImportResult, RawRecord

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class PluginPipelineResult:
    """Outcome of running Parser → … → Validator (Importer-ready records)."""

    path: str
    records: tuple[RawRecord, ...]
    skipped: int = 0
    stages_run: tuple[str, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        """True when at least one record survived validation.

        Soft per-row skips (validator rejects, normalize failures) are recorded
        in :attr:`errors` / :attr:`skipped` but do not fail the whole run.
        """
        return bool(self.records)

    def to_import_result(self) -> ImportResult:
        """Map to the plugin :class:`ImportResult` shape."""
        if self.errors and not self.records:
            return ImportResult.failure(
                self.errors[0],
                records_read=len(self.records) + self.skipped,
            )
        return ImportResult.from_records(
            self.records,
            skipped=self.skipped,
            errors=self.errors,
            metadata={"stages_run": list(self.stages_run)},
        )


class PluginPipeline:
    """Run the site-plugin ingest stages in canonical order.

    Stage callables are optional so simple importers can omit Downloader /
    Validator while still documenting the full chain.
    """

    stages: tuple[str, ...] = PLUGIN_PIPELINE_STAGES

    def __init__(
        self,
        *,
        downloader: IDocumentDownloader | None = None,
        parser: ISourceParser | None = None,
        extractor: ISourceExtractor | None = None,
        normalizer: ISourceNormalizer | None = None,
        validator: ISourceValidator | None = None,
    ) -> None:
        self._downloader = downloader
        self._parser = parser
        self._extractor = extractor
        self._normalizer = normalizer
        self._validator = validator

    def materialize(self, source: str | PathLike) -> Path:
        """Downloader stage (or passthrough for existing local files)."""
        text = str(source).strip()
        path = Path(text).expanduser()
        if self._downloader is None:
            if not path.exists():
                raise FileNotFoundError(f"Source not found: {path}")
            return path
        artifact = self._downloader.download(source)
        return artifact.path

    def run(self, source: str | PathLike) -> PluginPipelineResult:
        """Execute Downloader → Parser → Extractor → Normalizer → Validator."""
        stages_run: list[str] = []
        warnings: list[str] = []

        if self._downloader is not None:
            path = self.materialize(source)
            stages_run.append("downloader")
        else:
            path = Path(source).expanduser()
            if not path.exists():
                return PluginPipelineResult(
                    path=str(path),
                    records=(),
                    errors=(f"Source not found: {path}",),
                )

        if self._parser is None or self._extractor is None or self._normalizer is None:
            return PluginPipelineResult(
                path=str(path),
                records=(),
                stages_run=tuple(stages_run),
                errors=(
                    "PluginPipeline requires parser, extractor, and normalizer",
                ),
            )

        try:
            document = self._parser.parse(path)
            stages_run.append("parser")
        except Exception as exc:
            logger.exception("Plugin parser failed for %s", path)
            return PluginPipelineResult(
                path=str(path),
                records=(),
                stages_run=tuple(stages_run),
                errors=(f"parser failed: {exc}",),
            )

        try:
            extracted_items = _extract_items(self._extractor, document)
            stages_run.append("extractor")
        except Exception as exc:
            logger.exception("Plugin extractor failed for %s", path)
            return PluginPipelineResult(
                path=str(path),
                records=(),
                stages_run=tuple(stages_run),
                errors=(f"extraction failed: {exc}",),
            )

        records: list[RawRecord] = []
        skipped = 0
        errors: list[str] = []
        stages_run.append("normalizer")
        if self._validator is not None:
            stages_run.append("validator")

        for extracted in extracted_items:
            try:
                record = self._normalizer.normalize(extracted, document)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"normalize failed: {exc}")
                skipped += 1
                continue

            if self._validator is not None:
                result = self._validator.validate(record, extracted=extracted)
                warnings.extend(result.warnings)
                if not result.ok:
                    skipped += 1
                    errors.extend(result.errors)
                    continue

            records.append(dict(record))

        stages_run.append("importer")
        logger.info(
            "PluginPipeline complete path=%s records=%d skipped=%d stages=%s",
            path,
            len(records),
            skipped,
            "→".join(stages_run),
        )
        return PluginPipelineResult(
            path=str(path),
            records=tuple(records),
            skipped=skipped,
            stages_run=tuple(stages_run),
            errors=tuple(errors),
            warnings=tuple(warnings),
        )


def passthrough_validator(
    predicate: Callable[[RawRecord, Any], StageValidationResult],
) -> ISourceValidator:
    """Adapt a simple callable into :class:`ISourceValidator`."""

    class _Adapter:
        def validate(
            self,
            record: RawRecord,
            *,
            extracted: object | None = None,
        ) -> StageValidationResult:
            return predicate(record, extracted)

    return _Adapter()


def _extract_items(extractor: ISourceExtractor, document: object) -> list[object]:
    """Support both ``extract_many`` and single ``extract`` plugin APIs."""
    extract_many = getattr(extractor, "extract_many", None)
    if callable(extract_many):
        return list(extract_many(document))
    extract_one = getattr(extractor, "extract", None)
    if callable(extract_one):
        return [extract_one(document)]
    raise TypeError("Extractor must define extract_many() or extract()")


__all__ = [
    "PLUGIN_PIPELINE_STAGES",
    "PluginPipeline",
    "PluginPipelineResult",
    "passthrough_validator",
]
