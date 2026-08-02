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
from profile_intelligence.api.serializers import (
    comparison_to_dict,
    dashboard_to_dict,
    import_summary_to_dict,
    plugin_to_dict,
    profile_to_dict,
)
from profile_intelligence.core.exceptions import PipError, ValidationError
from profile_intelligence.core.logging import get_logger
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
    if method == "GET" and path == "/api/analytics":
        return 200, get_analytics(ctx, query)
    if method == "GET" and path == "/api/plugins":
        return 200, list_plugins(ctx)
    if method == "POST" and path == "/api/plugins/reload":
        return 200, reload_plugins(ctx)
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
    """POST /api/import/url — Downloader stage then Import."""
    url = str(body.get("url") or "").strip()
    if not url:
        raise ApiError("Field 'url' is required", status=400)
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ApiError("url must be http or https", status=400)
    if not ctx.config.media.allow_remote_download:
        raise ApiError(
            "Remote download disabled (media.allow_remote_download=false)",
            status=400,
        )

    plugin = _optional_str(body, "plugin")
    source = _optional_str(body, "source")
    downloader = ctx.downloader or DocumentDownloader(
        ctx.config.data_dir / "inbox" / "downloads",
        allow_remote=ctx.config.media.allow_remote_download,
        timeout_seconds=float(ctx.config.media.download_timeout_seconds),
    )
    try:
        artifact = downloader.download(url)
        summary = ctx.import_flow.run_import(
            artifact.path, source=source, plugin_name=plugin
        )
    except (OSError, PipError, ValueError) as exc:
        raise ApiError(str(exc), status=400) from exc

    payload = import_summary_to_dict(summary)
    payload["url"] = url
    payload["downloaded_path"] = str(artifact.path)
    return payload


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
    """GET /api/profiles."""
    limit = _int_param(query, "limit", default=50, minimum=1, maximum=10_000)
    offset = _int_param(query, "offset", default=0, minimum=0, maximum=1_000_000)
    q = (query.get("q") or "").strip()
    if q:
        rows = list(ctx.profiles.search(q, limit=limit))
        total = len(rows)
    else:
        rows = list(ctx.profiles.list_profiles(limit=limit, offset=offset))
        total = ctx.profiles.count()
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [profile_to_dict(row) for row in rows],
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
    return {
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


def list_plugins(ctx: ApiContext) -> dict[str, Any]:
    """GET /api/plugins."""
    plugins = ctx.importers.list_plugins()
    return {
        "count": len(plugins),
        "items": [plugin_to_dict(plugin) for plugin in plugins],
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
