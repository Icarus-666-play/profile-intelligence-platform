"""REST route handlers for the local JSON API."""

from __future__ import annotations

import base64
import re
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from profile_intelligence.api.context import ApiContext
from profile_intelligence.api.http import ApiError
from profile_intelligence.api.profile_filters import (
    ProfileListFilters,
    apply_profile_filters,
)
from profile_intelligence.api.profile_list import enrich_list_fields_from_database
from profile_intelligence.api.serializers import (
    comparison_to_dict,
    dashboard_to_dict,
    import_summary_to_dict,
    plugin_to_dict,
    preview_result_to_dict,
    profile_to_dict,
)
from profile_intelligence.core.exceptions import PipError, ValidationError
from profile_intelligence.core.logging import get_logger
from profile_intelligence.domain.interfaces.plugin_pipeline import DownloadArtifact
from profile_intelligence.infrastructure.auth import LocalAuthService
from profile_intelligence.infrastructure.download import DocumentDownloader

logger = get_logger(__name__)

_PROFILE_ID_RE = re.compile(r"^/api/profiles/(\d+)$")


def dispatch(
    ctx: ApiContext,
    *,
    method: str,
    path: str,
    query: dict[str, str],
    body: dict[str, Any],
) -> tuple[int, Any]:
    """Route an API call to a handler. Returns ``(status, payload)``."""
    if method == "POST" and path == "/api/import/url":
        return 200, import_url(ctx, body)
    if method == "POST" and path == "/api/import/url/preview":
        return 200, import_url_preview(ctx, body)
    if method == "GET" and path == "/api/import/activity":
        return 200, import_activity(ctx)
    if method == "POST" and path == "/api/import/files":
        return 200, import_files(ctx, body)
    if method == "GET" and path == "/api/profiles":
        return 200, list_profiles(ctx, query)
    match = _PROFILE_ID_RE.match(path)
    if method == "GET" and match:
        return 200, get_profile(ctx, int(match.group(1)))
    if method == "POST" and path == "/api/compare":
        return 200, compare_profiles(ctx, body)
    if method == "GET" and path == "/api/dashboard":
        return 200, get_dashboard(ctx)
    if method == "GET" and path == "/api/daily":
        return 200, get_daily(ctx)
    if method == "POST" and path == "/api/daily/run":
        return 200, run_daily(ctx, body)
    if method == "GET" and path == "/api/analytics":
        return 200, get_analytics(ctx, query)
    if method == "GET" and path == "/api/plugins":
        return 200, list_plugins(ctx)
    if method == "POST" and path == "/api/plugins/reload":
        return 200, reload_plugins(ctx)
    if method == "GET" and path == "/api/settings":
        return 200, get_settings(ctx)
    if method == "GET" and path == "/api/backups":
        return 200, list_backups(ctx)
    if method == "POST" and path == "/api/backups":
        return 200, create_backup(ctx)
    if method == "GET" and path == "/api/auth/status":
        return 200, auth_status(ctx)
    if method == "POST" and path == "/api/auth/login":
        return 200, auth_login(ctx, body)
    if method == "POST" and path == "/api/auth/guest":
        return 200, auth_guest(ctx)
    if method == "POST" and path == "/api/auth/logout":
        return 200, auth_logout(ctx, body)
    if method == "GET" and path == "/api/auth/session":
        return 200, auth_session(ctx, query)
    raise ApiError(f"Not found: {method} {path}", status=404)


def import_url(ctx: ApiContext, body: dict[str, Any]) -> dict[str, Any]:
    """POST /api/import/url — one or more URLs through Import."""
    from profile_intelligence.domain.value_objects.url_import import URL_IMPORT_STAGES

    urls, plugin, source = _url_import_list(ctx, body)
    results: list[dict[str, Any]] = []
    errors: list[str] = []
    for index, url in enumerate(urls, start=1):
        try:
            results.append(
                _import_one_url(
                    ctx,
                    url=url,
                    plugin=plugin,
                    source=source,
                    batch_label=f"{index}/{len(urls)}",
                )
            )
        except ApiError as exc:
            errors.append(f"{url}: {exc.message}")
            if ctx.import_activity is not None:
                ctx.import_activity.record_error(url=url, message=exc.message)
    if len(urls) == 1:
        if results:
            return results[0]
        raise ApiError(errors[0] if errors else "Import failed", status=400)
    return {
        "count": len(results),
        "imports": results,
        "errors": errors,
        "urls": list(urls),
        "pipeline": list(URL_IMPORT_STAGES),
        "ok": bool(results) and not errors,
    }


def import_url_preview(ctx: ApiContext, body: dict[str, Any]) -> dict[str, Any]:
    """POST /api/import/url/preview — one or more URLs through Preview."""
    from profile_intelligence.domain.value_objects.url_import import URL_IMPORT_STAGES

    urls, plugin, source = _url_import_list(ctx, body)
    results: list[dict[str, Any]] = []
    errors: list[str] = []
    for index, url in enumerate(urls, start=1):
        try:
            results.append(
                _preview_one_url(
                    ctx,
                    url=url,
                    plugin=plugin,
                    source=source,
                    batch_label=f"{index}/{len(urls)}",
                )
            )
        except ApiError as exc:
            errors.append(f"{url}: {exc.message}")
            if ctx.import_activity is not None:
                ctx.import_activity.record_error(url=url, message=exc.message)
    if len(urls) == 1:
        if results:
            return results[0]
        raise ApiError(errors[0] if errors else "Preview failed", status=400)
    first = results[0] if results else {}
    return {
        **first,
        "count": len(results),
        "previews": results,
        "errors": errors,
        "urls": list(urls),
        "pipeline": list(URL_IMPORT_STAGES),
        "ok": bool(results) and not errors,
    }


def import_activity(ctx: ApiContext) -> dict[str, Any]:
    """GET /api/import/activity — Recent URLs, Queue, Progress, Errors, Completed."""
    from profile_intelligence.domain.value_objects.url_import import (
        URL_IMPORT_STAGE_LABELS,
        URL_IMPORT_STAGES,
    )

    if ctx.import_activity is None:
        return {
            "recent_urls": [],
            "import_queue": [],
            "progress": None,
            "errors": [],
            "completed": [],
            "pipeline": list(URL_IMPORT_STAGES),
            "stage_labels": dict(URL_IMPORT_STAGE_LABELS),
        }
    snap = ctx.import_activity.snapshot()
    return {
        "recent_urls": snap.recent_urls,
        "import_queue": snap.import_queue,
        "progress": snap.progress,
        "errors": snap.errors,
        "completed": snap.completed,
        "pipeline": list(URL_IMPORT_STAGES),
        "stage_labels": dict(URL_IMPORT_STAGE_LABELS),
    }


def _url_progress(
    activity: Any,
    *,
    url: str,
    stage: str,
    message: str,
    snapshot: dict[str, Any] | None,
    percent_override: int | None = None,
) -> None:
    from profile_intelligence.domain.value_objects.url_import import (
        URL_IMPORT_STAGES,
        stage_percent,
        stages_through,
    )

    if activity is None:
        return
    if stage == "download":
        activity.remember_url(url)
    activity.set_progress(
        url=url,
        stage=stage,
        message=message,
        percent=(
            percent_override
            if percent_override is not None
            else stage_percent(stage)
        ),
        stages_run=list(stages_through(stage)),
        pipeline=list(URL_IMPORT_STAGES),
        snapshot=snapshot,
    )


def _url_import_list(
    ctx: ApiContext, body: dict[str, Any]
) -> tuple[list[str], str | None, str | None]:
    """Parse one or more URLs from ``url`` / ``urls`` fields."""
    if not ctx.config.media.allow_remote_download:
        raise ApiError(
            "Remote download disabled (media.allow_remote_download=false)",
            status=400,
        )
    collected: list[str] = []
    raw_urls = body.get("urls")
    if isinstance(raw_urls, list):
        collected.extend(str(item).strip() for item in raw_urls if str(item).strip())
    raw_url = body.get("url")
    if raw_url is not None:
        text = str(raw_url).replace("\r\n", "\n").replace("\r", "\n")
        collected.extend(
            line.strip() for line in text.split("\n") if line.strip()
        )
    # Deduplicate while preserving order; drop placeholders.
    urls: list[str] = []
    seen: set[str] = set()
    for item in collected:
        if item in seen:
            continue
        if _is_placeholder_url(item):
            continue
        parsed = urlparse(item)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ApiError(f"url must be http or https: {item}", status=400)
        seen.add(item)
        urls.append(item)
    if not urls:
        raise ApiError(
            "Provide at least one URL via 'url' or 'urls' (one per line)",
            status=400,
        )
    return urls, _optional_str(body, "plugin"), _optional_str(body, "source")


def _is_placeholder_url(url: str) -> bool:
    cleaned = url.strip().lower()
    if cleaned in {"https://", "http://", "https://...", "http://..."}:
        return True
    return cleaned.endswith("://...") or cleaned.endswith("://…")


def _import_one_url(
    ctx: ApiContext,
    *,
    url: str,
    plugin: str | None,
    source: str | None,
    batch_label: str | None = None,
) -> dict[str, Any]:
    from profile_intelligence.domain.value_objects.url_import import (
        URL_IMPORT_STAGES,
        UrlSnapshot,
        stage_percent,
        stages_through,
    )

    activity = ctx.import_activity
    prefix = f"[{batch_label}] " if batch_label else ""
    try:
        _url_progress(
            activity,
            url=url,
            stage="download",
            message=f"{prefix}Downloading…",
            snapshot=None,
        )
        artifact = _download_url(ctx, url)
        snapshot = UrlSnapshot.from_artifact(artifact)
        _url_progress(
            activity,
            url=url,
            stage="parse",
            message=f"{prefix}Parsing {snapshot.path.name}…",
            snapshot=snapshot.to_mapping(),
        )
        _url_progress(
            activity,
            url=url,
            stage="preview",
            message=f"{prefix}Preparing records…",
            snapshot=snapshot.to_mapping(),
        )
        _url_progress(
            activity,
            url=url,
            stage="import",
            message=f"{prefix}Importing into SQLite…",
            snapshot=snapshot.to_mapping(),
        )
        summary = ctx.import_flow.run_import(
            artifact.path, source=source, plugin_name=plugin
        )
    except (OSError, PipError, ValueError, ApiError) as exc:
        if activity is not None:
            activity.record_error(url=url, message=str(exc))
        if isinstance(exc, ApiError):
            raise
        raise ApiError(str(exc), status=400) from exc

    _url_progress(
        activity,
        url=url,
        stage="finished",
        message=f"{prefix}Finished",
        snapshot=snapshot.to_mapping(),
    )
    payload = import_summary_to_dict(summary)
    payload["url"] = url
    payload["downloaded_path"] = str(artifact.path)
    payload["snapshot"] = snapshot.to_mapping()
    payload["pipeline"] = list(URL_IMPORT_STAGES)
    payload["stages_run"] = list(stages_through("finished"))
    payload["stage"] = "finished"
    payload["percent"] = stage_percent("finished")
    if activity is not None:
        activity.record_completed(
            url=url,
            path=str(artifact.path),
            plugin=summary.plugin,
            created=summary.created,
            updated=summary.updated,
            success=summary.success,
            message=(
                None
                if summary.success
                else (summary.errors[0] if summary.errors else "import failed")
            ),
        )
    return payload


def _preview_one_url(
    ctx: ApiContext,
    *,
    url: str,
    plugin: str | None,
    source: str | None,
    batch_label: str | None = None,
) -> dict[str, Any]:
    from profile_intelligence.domain.value_objects.url_import import (
        URL_IMPORT_STAGES,
        UrlSnapshot,
        stage_percent,
        stages_through,
    )

    activity = ctx.import_activity
    prefix = f"[{batch_label}] " if batch_label else ""
    try:
        _url_progress(
            activity,
            url=url,
            stage="download",
            message=f"{prefix}Downloading…",
            snapshot=None,
        )
        artifact = _download_url(ctx, url)
        snapshot = UrlSnapshot.from_artifact(artifact)
        _url_progress(
            activity,
            url=url,
            stage="parse",
            message=f"{prefix}Parsing {snapshot.path.name}…",
            snapshot=snapshot.to_mapping(),
        )
        _url_progress(
            activity,
            url=url,
            stage="preview",
            message=f"{prefix}Building preview…",
            snapshot=snapshot.to_mapping(),
        )
        preview = ctx.import_flow.preview(
            artifact.path, source=source, plugin_name=plugin
        )
    except (OSError, PipError, ValueError, ApiError) as exc:
        if activity is not None:
            activity.record_error(url=url, message=str(exc))
        if isinstance(exc, ApiError):
            raise
        raise ApiError(str(exc), status=400) from exc

    if activity is not None:
        _url_progress(
            activity,
            url=url,
            stage="preview",
            message=f"{prefix}Preview ready",
            snapshot=snapshot.to_mapping(),
            percent_override=stage_percent("preview"),
        )
    payload = preview_result_to_dict(preview)
    payload["url"] = url
    payload["downloaded_path"] = str(artifact.path)
    payload["snapshot"] = snapshot.to_mapping()
    payload["pipeline"] = list(URL_IMPORT_STAGES)
    payload["stages_run"] = list(stages_through("preview"))
    payload["stage"] = "preview"
    payload["percent"] = stage_percent("preview")
    return payload


def _download_url(ctx: ApiContext, url: str) -> DownloadArtifact:
    downloader = ctx.downloader or DocumentDownloader(
        ctx.config.data_dir / "inbox" / "downloads",
        allow_remote=ctx.config.media.allow_remote_download,
        timeout_seconds=float(ctx.config.media.download_timeout_seconds),
    )
    return downloader.download(url)


def import_files(ctx: ApiContext, body: dict[str, Any]) -> dict[str, Any]:
    """POST /api/import/files — import local paths and/or inline files."""
    plugin = _optional_str(body, "plugin")
    source = _optional_str(body, "source")
    recursive = bool(body.get("recursive", False))

    raw_paths = body.get("paths", [])
    if raw_paths is None:
        raw_paths = []
    if not isinstance(raw_paths, list):
        raise ApiError("Field 'paths' must be a list of strings", status=400)
    paths_list: list[object] = list(raw_paths)

    raw_files = body.get("files", [])
    if raw_files is None:
        raw_files = []
    if not isinstance(raw_files, list):
        raise ApiError("Field 'files' must be a list of objects", status=400)
    files_list: list[object] = list(raw_files)

    if not paths_list and not files_list:
        raise ApiError("Provide 'paths' and/or 'files'", status=400)

    staged: list[Path] = []
    if files_list:
        staging = Path(tempfile.mkdtemp(prefix="pip-api-import-"))
        for index, item in enumerate(files_list):
            if not isinstance(item, dict):
                raise ApiError("Each files[] entry must be an object", status=400)
            name = str(item.get("name") or f"upload-{index}.bin")
            content_b64 = item.get("content_base64")
            if not isinstance(content_b64, str) or not content_b64:
                raise ApiError(
                    f"files[{index}].content_base64 is required",
                    status=400,
                )
            try:
                raw = base64.b64decode(content_b64, validate=True)
            except (ValueError, TypeError) as exc:
                raise ApiError(
                    f"files[{index}].content_base64 is invalid",
                    status=400,
                ) from exc
            safe_name = Path(name).name or f"upload-{index}.bin"
            dest = staging / safe_name
            dest.write_bytes(raw)
            staged.append(dest)

    targets = [Path(str(path)).expanduser() for path in paths_list] + staged
    results: list[dict[str, Any]] = []
    errors: list[str] = []

    for target in targets:
        try:
            if target.is_dir():
                summary = ctx.import_flow.run_import(
                    target,
                    source=source,
                    plugin_name=plugin,
                    recursive=recursive,
                )
            else:
                if not target.exists():
                    raise ApiError(f"Path not found: {target}", status=400)
                summary = ctx.import_flow.run_import(
                    target,
                    source=source,
                    plugin_name=plugin,
                )
            results.append(import_summary_to_dict(summary))
        except ApiError as exc:
            errors.append(exc.message)
        except (OSError, PipError, ValueError) as exc:
            errors.append(str(exc))

    return {
        "imports": results,
        "errors": errors,
        "count": len(results),
    }


def list_profiles(ctx: ApiContext, query: dict[str, str]) -> dict[str, Any]:
    """GET /api/profiles — optional ``q`` plus Show me filters."""
    limit = _int_param(query, "limit", default=50, minimum=1, maximum=10_000)
    offset = _int_param(query, "offset", default=0, minimum=0, maximum=1_000_000)
    q = (query.get("q") or "").strip()
    filters = ProfileListFilters.from_query(query)

    # When filters are active, scan a wider candidate set then filter/page
    # in memory (local-first; profile volumes stay modest).
    fetch_limit = max(limit + offset, 10_000) if filters.active else limit
    fetch_offset = 0 if filters.active else offset

    if q:
        rows = list(ctx.profiles.search(q, limit=fetch_limit))
    else:
        rows = list(
            ctx.profiles.list_profiles(limit=fetch_limit, offset=fetch_offset)
        )
    items = [profile_to_dict(row) for row in rows]
    enrich_list_fields_from_database(rows, ctx.database, items)
    if filters.active:
        items = apply_profile_filters(items, filters)
        total = len(items)
        items = items[offset : offset + limit]
    elif q:
        total = len(items)
    else:
        total = ctx.profiles.count()
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "filters": filters.to_mapping(),
        "items": items,
    }


def get_profile(ctx: ApiContext, profile_id: int) -> dict[str, Any]:
    """GET /api/profiles/{id}."""
    profile = ctx.repository.get_by_id(profile_id)
    if profile is None:
        raise ApiError(f"Profile not found: id={profile_id}", status=404)
    return profile_to_dict(profile)


def compare_profiles(ctx: ApiContext, body: dict[str, Any]) -> dict[str, Any]:
    """POST /api/compare."""
    left_raw = body.get("left_id", body.get("left"))
    right_raw = body.get("right_id", body.get("right"))
    if left_raw is None or right_raw is None:
        raise ApiError("left_id and right_id are required", status=400)
    try:
        left = int(str(left_raw))
        right = int(str(right_raw))
    except (TypeError, ValueError) as exc:
        raise ApiError(
            "left_id and right_id must be integers",
            status=400,
        ) from exc
    try:
        comparison = ctx.compare.compare_ids(left, right)
    except ValidationError as exc:
        raise ApiError(str(exc), status=400) from exc
    return comparison_to_dict(comparison)


def get_dashboard(ctx: ApiContext) -> dict[str, Any]:
    """GET /api/dashboard."""
    return dashboard_to_dict(ctx.dashboard.snapshot())


def get_analytics(ctx: ApiContext, query: dict[str, str]) -> dict[str, Any]:
    """GET /api/analytics — aggregate analysis snapshot."""
    from profile_intelligence.infrastructure.dashboard import (
        ReportsAnalyticsService,
        reports_analytics_to_dict,
    )

    threshold = query.get("threshold")
    thr = float(threshold) if threshold not in {None, ""} else None
    duplicates = ctx.analysis.find_duplicates(threshold=thr)
    classified = ctx.analysis.classify_all(limit=5_000)
    bands: dict[str, int] = {}
    completeness: dict[str, int] = {}
    for item in classified:
        bands[item.confidence_band] = bands.get(item.confidence_band, 0) + 1
        completeness[item.completeness_class] = (
            completeness.get(item.completeness_class, 0) + 1
        )
    snapshot = ctx.dashboard.snapshot()
    reports_service = ctx.reports_analytics or ReportsAnalyticsService(
        ctx.repository,
        database=ctx.database,
        analysis=ctx.analysis,
    )
    payload = {
        "profiles": snapshot.total_profiles,
        "scored_profiles": snapshot.scored_profiles,
        "average_score": snapshot.average_score,
        "by_source": [
            {"source": source, "count": count}
            for source, count in snapshot.by_source
        ],
        "duplicates": {
            "scanned": duplicates.scanned,
            "pairs": len(duplicates.pairs),
            "groups": len(duplicates.groups),
            "threshold": thr if thr is not None else 0.75,
        },
        "classification": {
            "count": len(classified),
            "confidence_bands": bands,
            "completeness": completeness,
        },
    }
    payload.update(reports_analytics_to_dict(reports_service.build()))
    return payload


def list_plugins(ctx: ApiContext) -> dict[str, Any]:
    """GET /api/plugins."""
    plugins = ctx.importers.list_plugins()
    return {
        "count": len(plugins),
        "items": [plugin_to_dict(plugin) for plugin in plugins],
    }


def get_settings(ctx: ApiContext) -> dict[str, Any]:
    """GET /api/settings — redacted configuration snapshot."""
    from profile_intelligence.api.settings_snapshot import settings_to_dict
    from profile_intelligence.infrastructure.backups import BackupService

    payload = settings_to_dict(ctx.config)
    backups = ctx.backups or BackupService(ctx.config)
    payload["backups"]["items"] = [
        {
            "name": item.name,
            "path": item.path,
            "size_bytes": item.size_bytes,
            "created_at": item.created_at,
        }
        for item in backups.list_backups()
    ]
    plugins = list_plugins(ctx)
    payload["plugins"]["count"] = plugins["count"]
    payload["plugins"]["items"] = plugins["items"]
    return payload


def list_backups(ctx: ApiContext) -> dict[str, Any]:
    """GET /api/backups."""
    from profile_intelligence.infrastructure.backups import BackupService

    backups = ctx.backups or BackupService(ctx.config)
    items = backups.list_backups()
    return {
        "directory": str(backups.backup_dir),
        "count": len(items),
        "items": [
            {
                "name": item.name,
                "path": item.path,
                "size_bytes": item.size_bytes,
                "created_at": item.created_at,
            }
            for item in items
        ],
    }


def create_backup(ctx: ApiContext) -> dict[str, Any]:
    """POST /api/backups — copy the SQLite database into exports/backups."""
    from profile_intelligence.infrastructure.backups import BackupService

    backups = ctx.backups or BackupService(ctx.config)
    try:
        item = backups.create_backup()
    except PipError as exc:
        raise ApiError(str(exc), status=400) from exc
    return {
        "ok": True,
        "backup": {
            "name": item.name,
            "path": item.path,
            "size_bytes": item.size_bytes,
            "created_at": item.created_at,
        },
    }


def reload_plugins(ctx: ApiContext) -> dict[str, Any]:
    """POST /api/plugins/reload."""
    enabled = ctx.config.importers.enabled or None
    count = ctx.importers.reload(
        plugins_dir=ctx.config.plugins_dir,
        enabled=enabled,
    )
    return {
        "reloaded": count,
        "items": [plugin_to_dict(plugin) for plugin in ctx.importers.list_plugins()],
    }


def _auth(ctx: ApiContext) -> LocalAuthService:
    if ctx.auth is None:
        raise ApiError("Auth service unavailable", status=500)
    return ctx.auth


def auth_status(ctx: ApiContext) -> dict[str, Any]:
    """GET /api/auth/status — Login (optional) configuration."""
    return _auth(ctx).status()


def auth_login(ctx: ApiContext, body: dict[str, Any]) -> dict[str, Any]:
    """POST /api/auth/login."""
    username = str(body.get("username") or "").strip()
    password = str(body.get("password") or "")
    try:
        session = _auth(ctx).login(username, password)
    except ValidationError as exc:
        raise ApiError(str(exc), status=401) from exc
    return {"session": session.to_dict(), "next": "/"}


def auth_guest(ctx: ApiContext) -> dict[str, Any]:
    """POST /api/auth/guest — skip optional login → Home."""
    try:
        session = _auth(ctx).continue_as_guest()
    except ValidationError as exc:
        raise ApiError(str(exc), status=403) from exc
    return {"session": session.to_dict(), "next": "/"}


def auth_logout(ctx: ApiContext, body: dict[str, Any]) -> dict[str, Any]:
    """POST /api/auth/logout."""
    token = _optional_str(body, "token")
    _auth(ctx).logout(token)
    return {"ok": True, "next": "/login"}


def auth_session(ctx: ApiContext, query: dict[str, str]) -> dict[str, Any]:
    """GET /api/auth/session?token=…"""
    token = (query.get("token") or "").strip() or None
    session = _auth(ctx).resolve(token)
    if session is None:
        return {"session": None}
    return {"session": session.to_dict()}


def get_daily(ctx: ApiContext) -> dict[str, Any]:
    """GET /api/daily — pipeline stages, labels, and latest progress."""
    from profile_intelligence.domain.value_objects.daily import (
        DAILY_STAGE_LABELS,
        DAILY_STAGES,
    )

    snap = (
        ctx.daily_activity.snapshot()
        if ctx.daily_activity is not None
        else {"progress": None, "last_result": None}
    )
    return {
        "pipeline": list(DAILY_STAGES),
        "stage_labels": dict(DAILY_STAGE_LABELS),
        "progress": snap.get("progress"),
        "last_result": snap.get("last_result"),
    }


def run_daily(ctx: ApiContext, body: dict[str, Any] | None = None) -> dict[str, Any]:
    """POST /api/daily/run — execute Every Day → … → Dashboard."""
    from profile_intelligence.core.exceptions import ServiceError
    from profile_intelligence.domain.value_objects.daily import (
        DAILY_STAGE_LABELS,
        DAILY_STAGES,
        stage_percent,
        stages_through,
    )

    if ctx.daily is None:
        raise ApiError("Daily pipeline is not configured", status=503)
    body = body or {}
    activity = ctx.daily_activity

    def on_progress(stage: str, message: str) -> None:
        if activity is None:
            return
        activity.set_progress(
            stage=stage,
            message=message,
            percent=stage_percent(stage),
            stages_run=list(stages_through(stage)),
            pipeline=list(DAILY_STAGES),
        )

    try:
        result = ctx.daily.run(
            import_dir=_optional_str(body, "import_dir"),
            excel_path=_optional_str(body, "excel_path"),
            dashboard_path=_optional_str(body, "dashboard_path"),
            force_all_files=bool(body.get("force_all_files", False)),
            on_progress=on_progress,
        )
    except (OSError, PipError, ServiceError, ValueError) as exc:
        if activity is not None:
            activity.record_result(
                {
                    "success": False,
                    "stage": "every_day",
                    "message": str(exc),
                    "percent": 0,
                    "stages_run": [],
                    "pipeline": list(DAILY_STAGES),
                    "errors": [str(exc)],
                }
            )
        raise ApiError(str(exc), status=400) from exc

    payload = {
        "ok": result.success,
        "success": result.success,
        "pipeline": list(DAILY_STAGES),
        "stage_labels": dict(DAILY_STAGE_LABELS),
        "stages_run": list(result.stages_run),
        "stage": result.stages_run[-1] if result.stages_run else "dashboard",
        "percent": stage_percent(
            result.stages_run[-1] if result.stages_run else "dashboard"
        ),
        "message": "Daily pipeline complete",
        "import_folder": result.import_folder,
        "files_detected": result.files_detected,
        "files_new": result.files_new,
        "files_imported": result.files_imported,
        "created": result.created,
        "updated": result.updated,
        "skipped": result.skipped,
        "profile_count": result.profile_count,
        "rescored": result.rescored,
        "images_extracted": result.images_extracted,
        "excel_path": result.excel_path,
        "dashboard_path": result.dashboard_path,
        "email_sent": result.email_sent,
        "email_skipped": result.email_skipped,
        "email_message": result.email_message,
        "events": list(result.event_names),
        "errors": list(result.errors),
    }
    if activity is not None:
        activity.record_result(payload)
    return payload


def _optional_str(body: dict[str, Any], key: str) -> str | None:
    value = body.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _int_param(
    query: dict[str, str],
    key: str,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    raw = query.get(key)
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ApiError(f"Query param '{key}' must be an integer", status=400) from exc
    return max(minimum, min(maximum, value))
