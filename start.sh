#!/usr/bin/env bash
# Start Profile Intelligence Platform (React + FastAPI).
#
#   ./start.sh
#   ./start.sh --host 127.0.0.1 --port 8765
#
# Equivalent to:
#   uvicorn profile_intelligence.api.main:app --reload

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

HOST="${PIP_HOST:-127.0.0.1}"
PORT="${PIP_PORT:-8765}"
RELOAD="${PIP_RELOAD:-1}"

usage() {
  cat <<'EOF'
Usage: ./start.sh [options]

Start the local FastAPI + React UI
(uvicorn profile_intelligence.api.main:app).

Options:
  --host HOST     Bind host (default: 127.0.0.1 or PIP_HOST)
  --port PORT     Bind port (default: 8765 or PIP_PORT)
  --no-reload     Disable uvicorn --reload
  -h, --help      Show this help

Environment:
  PIP_HOST, PIP_PORT, PIP_RELOAD (0 to disable reload)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      HOST="${2:?--host requires a value}"
      shift 2
      ;;
    --port)
      PORT="${2:?--port requires a value}"
      shift 2
      ;;
    --no-reload)
      RELOAD=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -f "$ROOT/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
elif [[ -f "$ROOT/.venv/Scripts/activate" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/.venv/Scripts/activate"
fi

if ! command -v uvicorn >/dev/null 2>&1; then
  echo "uvicorn not found. Install with: pip install -e \".[dev]\"" >&2
  exit 1
fi

export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:$PYTHONPATH}"

echo "Profile Intelligence Platform"
echo "Open: http://${HOST}:${PORT}/"
echo "API:  http://${HOST}:${PORT}/api/…"
echo "Docs: http://${HOST}:${PORT}/api/docs"
echo "Press Ctrl+C to stop."

RELOAD_ARGS=()
if [[ "$RELOAD" != "0" ]]; then
  RELOAD_ARGS+=(--reload)
fi

exec uvicorn profile_intelligence.api.main:app \
  --host "$HOST" \
  --port "$PORT" \
  "${RELOAD_ARGS[@]}"
