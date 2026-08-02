"""Import-related value objects."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

RawRecord = dict[str, Any]


@dataclass(frozen=True, slots=True)
class ImportResult:
    """Outcome of an import parse operation.

    Successful parsers populate :attr:`records` with raw row mappings.
    Persistence is handled by application use cases, not the plugin.
    """

    success: bool
    records_read: int = 0
    records_imported: int = 0
    records_skipped: int = 0
    records: tuple[Mapping[str, Any], ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def failure(cls, message: str, *, records_read: int = 0) -> ImportResult:
        """Convenience constructor for a failed import."""
        return cls(
            success=False,
            records_read=records_read,
            errors=(message,),
        )

    @classmethod
    def from_records(
        cls,
        records: Sequence[Mapping[str, Any]],
        *,
        skipped: int = 0,
        errors: tuple[str, ...] = (),
        metadata: dict[str, Any] | None = None,
    ) -> ImportResult:
        """Build a successful result from parsed raw records."""
        materialized = tuple(dict(record) for record in records)
        return cls(
            success=True,
            records_read=len(materialized) + skipped,
            records_imported=len(materialized),
            records_skipped=skipped,
            records=materialized,
            errors=errors,
            metadata=metadata or {},
        )
