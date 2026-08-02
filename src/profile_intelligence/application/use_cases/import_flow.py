"""Operator import flow: Input → Preview → Validate → Import.

This is the staged control surface for CLI/UI. Internal transform stages remain::

    parser → normalizer → validator → duplicate_detector → scorer → repository
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from profile_intelligence.application.pipeline.chain import ProcessingResult
from profile_intelligence.application.use_cases.import_pipeline import ImportPipeline
from profile_intelligence.application.use_cases.import_service import (
    ImportService,
    ImportSummary,
)
from profile_intelligence.core.exceptions import ImporterError, ValidationError
from profile_intelligence.core.logging import get_logger
from profile_intelligence.core.types import PathLike
from profile_intelligence.domain.entities.profile import ProfileDraft
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
            _preview_row_from_draft(
                draft,
                index=index,
                status=status,
                messages=messages,
            )
        )
        index += 1

    for match in processed.duplicates:
        draft = match.draft
        rows.append(
            _preview_row_from_draft(
                draft,
                index=index,
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


def _preview_row_from_draft(
    draft: ProfileDraft,
    *,
    index: int,
    status: str,
    messages: tuple[str, ...] = (),
) -> PreviewRow:
    raw = _raw_mapping(draft.raw_json)
    languages = _as_string_list(raw.get("languages"))
    if not languages and draft.tags:
        # Best-effort: nationality/languages often land in tags for site plugins.
        languages = ()
    services = tuple(
        service.name for service in draft.services if service.name
    ) or tuple(_as_string_list(raw.get("services")))
    rates = tuple(_format_rate(rate) for rate in draft.rates) or tuple(
        _format_rate_mapping(item) for item in _as_mapping_list(raw.get("rates"))
    )
    reviews = tuple(_format_review(review) for review in draft.reviews) or tuple(
        _format_review_mapping(item)
        for item in _as_mapping_list(raw.get("reviews"))
    )
    picture_urls = tuple(
        photo.original_url for photo in draft.photos if photo.original_url
    )
    if not picture_urls:
        picture_urls = tuple(
            url
            for url in (
                *(_photo_url(raw.get("main_image")),),
                *(_photo_url(item) for item in _as_mapping_list(raw.get("gallery"))),
                *(_photo_url(item) for item in _as_mapping_list(raw.get("photos"))),
            )
            if url
        )
    main = next(
        (photo.original_url for photo in draft.photos if photo.role == "main"),
        None,
    )
    if main is None and picture_urls:
        main = picture_urls[0]

    age = _as_optional_text(raw.get("age"))
    nationality = _as_optional_text(raw.get("nationality"))
    return PreviewRow(
        index=index,
        display_name=draft.display_name,
        email=draft.email,
        organization=draft.organization,
        source=draft.source,
        score=draft.score,
        status=status,
        messages=messages,
        picture=main,
        age=age,
        nationality=nationality,
        languages=languages,
        services=services,
        rates=tuple(item for item in rates if item),
        reviews=tuple(item for item in reviews if item),
        pictures=picture_urls,
        location=draft.location,
    )


def _raw_mapping(raw_json: str | None) -> dict[str, Any]:
    if not raw_json:
        return {}
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _as_optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_string_list(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        parts = [part.strip() for part in re.split(r"[,/;|]", value) if part.strip()]
        return tuple(parts)
    if isinstance(value, (list, tuple)):
        items: list[str] = []
        for item in value:
            if isinstance(item, dict):
                name = item.get("name") or item.get("service")
                if name:
                    items.append(str(name).strip())
            else:
                text = str(item).strip()
                if text:
                    items.append(text)
        return tuple(items)
    return ()


def _as_mapping_list(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _photo_url(value: object) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, dict):
        return _as_optional_text(
            value.get("original_url") or value.get("url") or value.get("src")
        )
    return None


def _format_rate(rate: object) -> str:
    duration = getattr(rate, "duration", "") or ""
    price = getattr(rate, "price", "") or ""
    currency = getattr(rate, "currency", "") or ""
    bits = [str(duration).strip(), str(price).strip()]
    if currency:
        bits.append(str(currency).strip())
    text = " ".join(bit for bit in bits if bit)
    return text


def _format_rate_mapping(item: dict[str, Any]) -> str:
    duration = str(item.get("duration") or "").strip()
    price = str(item.get("price") or "").strip()
    currency = str(item.get("currency") or "").strip()
    return " ".join(bit for bit in (duration, price, currency) if bit)


def _format_review(review: object) -> str:
    author = getattr(review, "author", None)
    rating = getattr(review, "rating", None)
    text = getattr(review, "text", None)
    parts = [
        str(part).strip()
        for part in (rating, author, text)
        if part not in (None, "")
    ]
    return " — ".join(parts)


def _format_review_mapping(item: dict[str, Any]) -> str:
    parts = [
        str(part).strip()
        for part in (
            item.get("rating"),
            item.get("author"),
            item.get("text") or item.get("body"),
        )
        if part not in (None, "")
    ]
    return " — ".join(parts)


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
