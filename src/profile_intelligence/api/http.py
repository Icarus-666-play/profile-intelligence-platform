"""Minimal JSON/WSGI helpers for the local REST API."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping
from typing import Any
from urllib.parse import parse_qs

StartResponse = Callable[[str, list[tuple[str, str]]], Any]
JsonDict = dict[str, Any]


class ApiError(Exception):
    """HTTP-aware API error."""

    def __init__(self, message: str, *, status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


def read_body(environ: Mapping[str, Any]) -> bytes:
    """Read the WSGI request body."""
    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
    except (TypeError, ValueError):
        length = 0
    if length <= 0:
        return b""
    stream = environ["wsgi.input"]
    return bytes(stream.read(length))


def parse_json_body(environ: Mapping[str, Any]) -> JsonDict:
    """Parse a JSON object body (empty object when no body)."""
    raw = read_body(environ)
    if not raw.strip():
        return {}
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ApiError(f"Invalid JSON body: {exc}", status=400) from exc
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise ApiError("JSON body must be an object", status=400)
    return payload


def query_params(environ: Mapping[str, Any]) -> dict[str, str]:
    """Return the first value for each query parameter."""
    parsed = parse_qs(str(environ.get("QUERY_STRING") or ""))
    return {key: values[0] for key, values in parsed.items() if values}


def json_response(
    start_response: StartResponse,
    payload: Mapping[str, object] | list[object] | str | int | float | bool | None,
    *,
    status: int = 200,
) -> Iterable[bytes]:
    """Send a JSON response."""
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    reason = _STATUS.get(status, "OK" if status < 400 else "Error")
    start_response(
        f"{status} {reason}",
        [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(body))),
            ("Cache-Control", "no-store"),
        ],
    )
    return [body]


def error_response(
    start_response: StartResponse,
    message: str,
    *,
    status: int = 400,
) -> Iterable[bytes]:
    """Send a JSON error envelope."""
    return json_response(
        start_response,
        {"error": message, "status": status},
        status=status,
    )


_STATUS: dict[int, str] = {
    200: "OK",
    201: "Created",
    400: "Bad Request",
    404: "Not Found",
    405: "Method Not Allowed",
    409: "Conflict",
    500: "Internal Server Error",
    501: "Not Implemented",
}
