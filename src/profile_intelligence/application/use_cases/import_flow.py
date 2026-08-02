"""Operator import flow: Input → Preview → Validate → Import.

This is the staged control surface for CLI/UI. Internal transform stages remain::

    parser → normalizer → validator → duplicate_detector → scorer → repository
"""

from __future__ import annotations

import re
from pathlib import Path

from profile_intelligence.application.pipeline.chain import ProcessingResult
from profile_intelligence.application.use_cases.import_pipeline import ImportPipeline
from profile_intelligence.application.use_cases.import_service import (
    ImportService,
    ImportSummary,
)
from profile_intelligence.core.exceptions import ImporterError, ValidationError
from profile_intelligence.core.logging import get_logger
from profile_intelligence.core.types import PathLike
from profile_intelligence.domain.value_objects.documents import RawDocument
from profile_intelligence.domain.value_objects.import_flow import (
    IMPORT_FLOW_STAGES,
    InputResolution,
    PreviewResult,
    PreviewRow,
    ValidationIssue,
    ValidationResult,
)
from profile_intelligence.infrastructure.importers.registry import ImporterRegistry

logger = get_logger(__name__)

_ROW_RE = re.compile(r"^row\s+(\d+)\s*:\s*(.*)$", re.IGNORECASE)


class ImportFlow:
    """Staged operator workflow over :class:`ImportService` / :class:`ImportPipeline`.

    ```
    Input
     ↓
    Preview
     ↓
    Validate
     ↓
    Import
    ```
    """

    stages: tuple[str, ...] = IMPORT_FLOW_STAGES

    def __init__(
        self,
        import_service: ImportService,
        *,
        registry: ImporterRegistry | None = None,
        pipeline: ImportPipeline | None = None,
    ) -> None:
        self._imports = import_service
        self._pipeline = pipeline or import_service.pipeline
        self._registry = registry

    # --- Input -------------------------------------------------------------

    def resolve_input(
        self,
        path: PathLike,
        *,
        source: str | None = None,
        plugin_name: str | None = None,
    ) -> InputResolution:
        """Input stage: resolve local path and importer plugin."""
        resolved = Path(path).expanduser()
        if not resolved.exists():
            return InputResolution(
                path=str(resolved),
                plugin=plugin_name or "",
                source=source,
                exists=False,
                errors=(f"Path not found: {resolved}",),
            )

        if resolved.is_dir():
            return InputResolution(
                path=str(resolved.resolve()),
                plugin=plugin_name or "auto",
                source=source,
                is_directory=True,
                errors=()
                if plugin_name or self._has_any_handler(resolved)
                else ("No importer plugins available for directory contents",),
            )

        try:
            plugin = self._imports.resolve_importer(
                resolved, plugin_name=plugin_name
            )
        except (ImporterError, FileNotFoundError, ValueError) as exc:
            return InputResolution(
                path=str(resolved.resolve()),
                plugin=plugin_name or "",
                source=source,
                errors=(str(exc),),
            )

        logger.info("Import flow Input: path=%s plugin=%s", resolved, plugin.name)
        return InputResolution(
            path=str(resolved.resolve()),
            plugin=plugin.name,
            source=source,
            is_directory=False,
        )

    # --- Preview -----------------------------------------------------------

    def preview(
        self,
        path: PathLike,
        *,
        source: str | None = None,
        plugin_name: str | None = None,
    ) -> PreviewResult:
        """Preview stage: dry-run through scorer (no repository write)."""
        resolved_input = self.resolve_input(
            path, source=source, plugin_name=plugin_name
        )
        if not resolved_input.ok:
            return PreviewResult(
                path=resolved_input.path,
                plugin=resolved_input.plugin,
                records_read=0,
                rows=(),
                accepted_count=0,
                rejected_count=0,
                duplicate_count=0,
                update_count=0,
                errors=resolved_input.errors
                or ("Input stage failed",),
            )
        if resolved_input.is_directory:
            return PreviewResult(
                path=resolved_input.path,
                plugin=resolved_input.plugin,
                records_read=0,
                rows=(),
                accepted_count=0,
                rejected_count=0,
                duplicate_count=0,
                update_count=0,
                errors=(
                    "Preview supports a single file; choose one file path",
                ),
            )

        document = RawDocument.from_path(
            resolved_input.path,
            source=source,
            plugin_name=plugin_name or resolved_input.plugin,
        )
        processed = self._pipeline.process_document(document, source=source)
        result = _preview_from_processing(processed)
        logger.info(
            "Import flow Preview: path=%s accepted=%d rejected=%d",
            result.path,
            result.accepted_count,
            result.rejected_count,
        )
        return result

    # --- Validate ----------------------------------------------------------

    def validate(
        self,
        path: PathLike,
        *,
        source: str | None = None,
        plugin_name: str | None = None,
        require_accepted: bool = True,
    ) -> ValidationResult:
        """Validate stage: gate on validation / acceptance before Import."""
        preview = self.preview(path, source=source, plugin_name=plugin_name)
        issues: list[ValidationIssue] = []
        for error in preview.errors:
            issues.append(
                ValidationIssue(index=None, severity="error", message=error)
            )
        for row in preview.rows:
            if row.status == "invalid":
                for message in row.messages or ("invalid row",):
                    issues.append(
                        ValidationIssue(
                            index=row.index,
                            severity="error",
                            message=message,
                        )
                    )
            elif row.status == "duplicate":
                for message in row.messages or ("duplicate",):
                    issues.append(
                        ValidationIssue(
                            index=row.index,
                            severity="warning",
                            message=message,
                        )
                    )

        # Also parse structured validation_errors from preview errors list
        for error in preview.errors:
            match = _ROW_RE.match(error.strip())
            if match:
                issues.append(
                    ValidationIssue(
                        index=int(match.group(1)),
                        severity="error",
                        message=match.group(2),
                    )
                )

        unique_issues = _dedupe_issues(tuple(issues))
        rejected = preview.rejected_count
        accepted = preview.accepted_count
        hard_errors = tuple(
            issue for issue in unique_issues if issue.severity == "error"
        )
        if require_accepted:
            ok = accepted > 0
        else:
            ok = not hard_errors

        result = ValidationResult(
            path=preview.path,
            plugin=preview.plugin,
            ok=ok,
            accepted=accepted,
            rejected=rejected,
            issues=unique_issues,
            warnings=tuple(
                issue.message
                for issue in unique_issues
                if issue.severity == "warning"
            ),
        )
        logger.info(
            "Import flow Validate: path=%s ok=%s accepted=%d rejected=%d",
            result.path,
            result.ok,
            result.accepted,
            result.rejected,
        )
        return result

    # --- Import ------------------------------------------------------------

    def run_import(
        self,
        path: PathLike,
        *,
        source: str | None = None,
        plugin_name: str | None = None,
        recursive: bool = False,
        require_valid: bool = False,
    ) -> ImportSummary:
        """Import stage: persist through the full pipeline.

        When *require_valid* is True, raise :class:`ValidationError` if the
        Validate stage fails the gate.
        """
        target = Path(path)
        if require_valid and target.is_file():
            gate = self.validate(
                target, source=source, plugin_name=plugin_name
            )
            if not gate.ok:
                raise ValidationError(
                    f"Validate stage blocked Import: "
                    f"accepted={gate.accepted} rejected={gate.rejected}"
                )

        if target.is_dir():
            summary = self._imports.import_directory(
                target,
                source=source,
                plugin_name=plugin_name,
                recursive=recursive,
            )
        else:
            summary = self._imports.import_path(
                target,
                source=source,
                plugin_name=plugin_name,
            )
        logger.info(
            "Import flow Import: path=%s created=%d updated=%d skipped=%d",
            summary.path,
            summary.created,
            summary.updated,
            summary.skipped,
        )
        return summary

    def _has_any_handler(self, directory: Path) -> bool:
        registry = self._registry
        if registry is None:
            return True
        if not registry.list_plugins():
            return False
        for path in directory.iterdir():
            if path.is_file() and registry.find_handler(path) is not None:
                return True
        return False


def _preview_from_processing(processed: ProcessingResult) -> PreviewResult:
    rows: list[PreviewRow] = []
    index = 1

    update_keys = {
        id(match.draft): match for match in processed.update_matches
    }
    for draft in processed.scored or processed.unique or processed.validated:
        match = update_keys.get(id(draft))
        status = "update" if match is not None else "ok"
        messages: tuple[str, ...] = ()
        if match is not None:
            messages = (match.reason,)
        rows.append(
            PreviewRow(
                index=index,
                display_name=draft.display_name,
                email=draft.email,
                organization=draft.organization,
                source=draft.source,
                score=draft.score,
                status=status,
                messages=messages,
            )
        )
        index += 1

    for match in processed.duplicates:
        draft = match.draft
        rows.append(
            PreviewRow(
                index=index,
                display_name=draft.display_name,
                email=draft.email,
                organization=draft.organization,
                source=draft.source,
                score=draft.score,
                status="duplicate",
                messages=(match.reason,),
            )
        )
        index += 1

    for error in processed.validation_errors:
        row_match = _ROW_RE.match(error.strip())
        rows.append(
            PreviewRow(
                index=int(row_match.group(1)) if row_match else index,
                display_name="(invalid)",
                status="invalid",
                messages=(row_match.group(2) if row_match else error,),
            )
        )
        index += 1

    accepted = len(processed.scored or processed.unique or processed.validated)
    rejected = len(processed.validation_errors) + len(processed.normalize_errors)
    return PreviewResult(
        path=str(processed.parsed.path),
        plugin=processed.parsed.plugin_name,
        records_read=processed.parsed.records_read,
        rows=tuple(rows),
        accepted_count=accepted,
        rejected_count=rejected,
        duplicate_count=len(processed.duplicates),
        update_count=len(processed.update_matches),
        stages_run=processed.stages_run,
        errors=processed.errors,
    )


def _dedupe_issues(issues: tuple[ValidationIssue, ...]) -> tuple[ValidationIssue, ...]:
    seen: set[tuple[int | None, str, str]] = set()
    out: list[ValidationIssue] = []
    for issue in issues:
        key = (issue.index, issue.severity, issue.message)
        if key in seen:
            continue
        seen.add(key)
        out.append(issue)
    return tuple(out)


__all__ = ["IMPORT_FLOW_STAGES", "ImportFlow"]
