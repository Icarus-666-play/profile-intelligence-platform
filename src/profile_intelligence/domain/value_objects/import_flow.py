"""Operator import flow value objects.

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

from __future__ import annotations

from dataclasses import dataclass, field

IMPORT_FLOW_STAGES: tuple[str, ...] = (
    "input",
    "preview",
    "validate",
    "import",
)


@dataclass(frozen=True, slots=True)
class InputResolution:
    """Resolved Input stage: local path + selected plugin."""

    path: str
    plugin: str
    source: str | None = None
    is_directory: bool = False
    exists: bool = True
    errors: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        """True when the input can proceed to Preview."""
        return self.exists and not self.errors and bool(self.plugin)


@dataclass(frozen=True, slots=True)
class PreviewRow:
    """One previewable profile row after normalize/score (no persist)."""

    index: int
    display_name: str
    email: str | None = None
    organization: str | None = None
    source: str | None = None
    score: int | None = None
    status: str = "ok"  # ok | update | duplicate | invalid
    messages: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class PreviewResult:
    """Preview stage outcome (dry-run through scorer, no repository)."""

    path: str
    plugin: str
    records_read: int
    rows: tuple[PreviewRow, ...]
    accepted_count: int
    rejected_count: int
    duplicate_count: int
    update_count: int
    stages_run: tuple[str, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        """True when at least one row is ready to import."""
        return self.accepted_count > 0


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """One validation issue surfaced to the operator."""

    index: int | None
    severity: str  # error | warning
    message: str
    field: str | None = None


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Validate stage gate before Import commit."""

    path: str
    plugin: str
    ok: bool
    accepted: int
    rejected: int
    issues: tuple[ValidationIssue, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)


__all__ = [
    "IMPORT_FLOW_STAGES",
    "InputResolution",
    "PreviewResult",
    "PreviewRow",
    "ValidationIssue",
    "ValidationResult",
]
