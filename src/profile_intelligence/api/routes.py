"""REST route handlers for the local JSON API."""

from __future__ import annotations

import base64
import re
import tempfile
import urllib.error
import urllib.request
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
    raise ApiError(f"Not found: {method} {path}", status=404)


def import_url(ctx: ApiContext, body: dict[str, Any]) -> dict[str, Any]:
    """POST /api/import/url — download a URL then run Import."""
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
    timeout = float(ctx.config.media.download_timeout_seconds)

    suffix = Path(parsed.path).suffix or ".bin"
    try:
        content = _download_http(url, timeout=timeout)
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        raise ApiError(f"Failed to download url: {exc}", status=400) from exc

    inbox = ctx.config.data_dir / "inbox" / "api-url"
    inbox.mkdir(parents=True, exist_ok=True)
    target = inbox / f"download{suffix}"
    target.write_bytes(content)

    try:
        summary = ctx.import_flow.run_import(
            target, source=source, plugin_name=plugin
        )
    except (OSError, PipError, ValueError) as exc:
        raise ApiError(str(exc), status=400) from exc

    payload = import_summary_to_dict(summary)
    payload["url"] = url
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


def _download_http(url: str, *, timeout: float) -> bytes:
    """Fetch an http(s) URL into memory (scheme pre-validated by caller)."""
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "ProfileIntelligencePlatform/0.1"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return bytes(response.read())


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
