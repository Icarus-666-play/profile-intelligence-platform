"""JSON serializers for the local REST API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from profile_intelligence.application.use_cases.compare_service import (
    ProfileComparison,
)
from profile_intelligence.application.use_cases.import_service import ImportSummary
from profile_intelligence.domain.interfaces.importers import ImporterPlugin
from profile_intelligence.domain.interfaces.repositories import ProfileEntity
from profile_intelligence.domain.value_objects.import_flow import PreviewResult
from profile_intelligence.infrastructure.dashboard import DashboardSnapshot


def profile_to_dict(profile: ProfileEntity) -> dict[str, Any]:
    """Serialize a profile entity."""
    return {
        "id": profile.id,
        "external_id": profile.external_id,
        "display_name": profile.display_name,
        "email": profile.email,
        "phone": profile.phone,
        "title": profile.title,
        "organization": profile.organization,
        "location": profile.location,
        "tags": profile.tags,
        "source": profile.source,
        "notes": profile.notes,
        "score": profile.score,
        "created_at": _dt(profile.created_at),
        "updated_at": _dt(profile.updated_at),
    }


def plugin_to_dict(plugin: ImporterPlugin) -> dict[str, Any]:
    """Serialize an importer plugin."""
    return {
        "name": plugin.name,
        "description": plugin.description or "",
        "supported_extensions": list(plugin.supported_extensions),
    }


def dashboard_to_dict(snapshot: DashboardSnapshot) -> dict[str, Any]:
    """Serialize a dashboard snapshot."""
    return {
        "total_profiles": snapshot.total_profiles,
        "scored_profiles": snapshot.scored_profiles,
        "average_score": snapshot.average_score,
        "imported_today": snapshot.imported_today,
        "countries": snapshot.countries,
        "average_price": snapshot.average_price,
        "average_price_currency": snapshot.average_price_currency,
        "average_rating": snapshot.average_rating,
        "by_source": [
            {"source": source, "count": count}
            for source, count in snapshot.by_source
        ],
        "top_profiles": [profile_to_dict(row) for row in snapshot.top_profiles],
        "incomplete_profiles": [
            profile_to_dict(row) for row in snapshot.incomplete_profiles
        ],
        "newest_profiles": [
            profile_to_dict(row) for row in snapshot.newest_profiles
        ],
        "latest_imports": [
            {
                "path": item.path,
                "name": item.name,
                "imported_at": item.imported_at,
                "file_size": item.file_size,
            }
            for item in snapshot.latest_imports
        ],
        "duplicates": [
            {
                "left_id": item.left_id,
                "right_id": item.right_id,
                "left_name": item.left_name,
                "right_name": item.right_name,
                "score": item.score,
            }
            for item in snapshot.duplicates
        ],
        "import_queue": [
            {
                "path": item.path,
                "name": item.name,
                "file_size": item.file_size,
            }
            for item in snapshot.import_queue
        ],
    }


def comparison_to_dict(comparison: ProfileComparison) -> dict[str, Any]:
    """Serialize a profile comparison."""
    return {
        "left_id": comparison.left_id,
        "right_id": comparison.right_id,
        "left_name": comparison.left_name,
        "right_name": comparison.right_name,
        "differences": len(comparison.differences),
        "matches": len(comparison.matches),
        "fields": [
            {
                "field": item.field,
                "left": item.left,
                "right": item.right,
                "equal": item.equal,
            }
            for item in comparison.fields
        ],
    }


def import_summary_to_dict(summary: ImportSummary) -> dict[str, Any]:
    """Serialize an import summary."""
    return {
        "path": summary.path,
        "plugin": summary.plugin,
        "records_read": summary.records_read,
        "created": summary.created,
        "updated": summary.updated,
        "skipped": summary.skipped,
        "written": summary.written,
        "success": summary.success,
        "errors": list(summary.errors),
        "stats": {
            "profiles": summary.stats.profiles,
            "services": summary.stats.services,
            "rates": summary.stats.rates,
            "images": summary.stats.images,
            "duplicates": summary.stats.duplicates,
            "execution_seconds": summary.stats.execution_seconds,
        },
    }


def preview_result_to_dict(result: PreviewResult) -> dict[str, Any]:
    """Serialize an :class:`PreviewResult`."""
    return {
        "path": result.path,
        "plugin": result.plugin,
        "records_read": result.records_read,
        "accepted_count": result.accepted_count,
        "rejected_count": result.rejected_count,
        "duplicate_count": result.duplicate_count,
        "update_count": result.update_count,
        "ok": result.ok,
        "errors": list(result.errors),
        "stages_run": list(result.stages_run),
        "rows": [
            {
                "index": row.index,
                "display_name": row.display_name,
                "email": row.email,
                "organization": row.organization,
                "source": row.source,
                "score": row.score,
                "status": row.status,
                "messages": list(row.messages),
            }
            for row in result.rows
        ],
    }


def _dt(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()
