"""Reporting adapters (Excel already lives under ``excel/``; email is future)."""

from __future__ import annotations

from profile_intelligence.infrastructure.reporting.email_report import (
    EmailReportRequest,
    EmailReportResult,
    EmailReportService,
)

__all__ = [
    "EmailReportRequest",
    "EmailReportResult",
    "EmailReportService",
]
