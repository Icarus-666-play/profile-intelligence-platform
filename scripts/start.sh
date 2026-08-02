#!/usr/bin/env bash
# Start Profile Intelligence Platform — backend (FastAPI) + frontend (Vite).
#
#   ./scripts/start.sh
#
# Backend:  http://127.0.0.1:8000
# Frontend: http://localhost:5173
# Swagger:  http://127.0.0.1:8000/api/docs

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BACKEND_HOST="${PIP_HOST:-127.0.0.1}"
BACKEND_PORT="${PIP_PORT:-8000}"
FRONTEND_HOST="${PIP_FRONTEND_HOST:-localhost}"
FRONTEND_PORT="${PIP_FRONTEND_PORT:-5173}"
BACKEND_URL="http://${BACKEND_HOST}:${BACKEND_PORT}"
FRONTEND_URL="http://${FRONTEND_HOST}:${FRONTEND_PORT}"
OPEN_BROWSER="${PIP_OPEN_BROWSER:-1}"

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  if [[ -n "${FRONTEND_PID}" ]] && kill -0 "${FRONTEND_PID}" 2>/dev/null; then
    kill "${FRONTEND_PID}" 2>/dev/null || true
  fi
  if [[ -n "${BACKEND_PID}" ]] && kill -0 "${BACKEND_PID}" 2>/dev/null; then
    kill "${BACKEND_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

echo "Profile Intelligence Platform — starting…"

# Activate virtualenv when present.
if [[ -f "$ROOT/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
elif [[ -f "$ROOT/.venv/Scripts/activate" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/.venv/Scripts/activate"
fi

# Verify Python version (3.12+).
if ! command -v python >/dev/null 2>&1 && ! command -v python3 >/dev/null 2>&1; then
  echo "Python not found. Install Python 3.12+ first." >&2
  exit 1
fi
PYTHON_BIN="$(command -v python3 2>/dev/null || command -v python)"
"$PYTHON_BIN" - <<'PY'
import sys
if sys.version_info < (3, 12):
    raise SystemExit(
        f"Python 3.12+ required (found {sys.version.split()[0]})"
    )
print(f"Python {sys.version.split()[0]}")
PY

# Install missing Python dependencies.
if ! "$PYTHON_BIN" -c "import profile_intelligence, fastapi, uvicorn" 2>/dev/null; then
  echo "Installing Python package (editable + dev)…"
  "$PYTHON_BIN" -m pip install -U pip
  "$PYTHON_BIN" -m pip install -e ".[dev]"
fi

export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:$PYTHONPATH}"

# Start FastAPI backend.
echo "Starting backend on ${BACKEND_URL} …"
uvicorn profile_intelligence.api.main:app \
  --host "${BACKEND_HOST}" \
  --port "${BACKEND_PORT}" \
  --reload &
BACKEND_PID=$!

# Wait until /api/health responds.
echo "Waiting for backend health…"
backend_ready=0
for _ in {1..60}; do
  if curl -fsS "${BACKEND_URL}/api/health" >/dev/null 2>&1; then
    echo "Backend ready."
    backend_ready=1
    break
  fi
  if ! kill -0 "${BACKEND_PID}" 2>/dev/null; then
    echo "Backend process exited unexpectedly." >&2
    exit 1
  fi
  sleep 0.5
done
if [[ "${backend_ready}" != "1" ]]; then
  echo "Backend did not become healthy in time." >&2
  exit 1
fi

# Start React dev server when frontend/ exists.
if [[ -d "$ROOT/frontend" && -f "$ROOT/frontend/package.json" ]]; then
  if ! command -v npm >/dev/null 2>&1; then
    echo "npm not found; skipping React dev server. Backend remains at ${BACKEND_URL}" >&2
  else
    if [[ ! -d "$ROOT/frontend/node_modules" ]]; then
      echo "Installing frontend dependencies…"
      (cd "$ROOT/frontend" && npm install)
    fi
    echo "Starting frontend on ${FRONTEND_URL} …"
    (cd "$ROOT/frontend" && npm run dev -- --host "${FRONTEND_HOST}" --port "${FRONTEND_PORT}") &
    FRONTEND_PID=$!
    for _ in {1..60}; do
      if curl -fsS "${FRONTEND_URL}/" >/dev/null 2>&1; then
        echo "Frontend ready."
        break
      fi
      sleep 0.5
    done
  fi
else
  echo "No frontend/ directory — serving API (and built SPA if present) only."
fi

OPEN_URL="${FRONTEND_URL}"
if [[ -z "${FRONTEND_PID}" ]]; then
  OPEN_URL="${BACKEND_URL}/"
fi

echo ""
echo "Backend:  ${BACKEND_URL}/"
echo "API docs: ${BACKEND_URL}/api/docs"
if [[ -n "${FRONTEND_PID}" ]]; then
  echo "Frontend: ${FRONTEND_URL}/"
fi
echo "Press Ctrl+C to stop."
echo ""

if [[ "${OPEN_BROWSER}" != "0" ]]; then
  if command -v open >/dev/null 2>&1; then
    open "${OPEN_URL}" >/dev/null 2>&1 || true
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "${OPEN_URL}" >/dev/null 2>&1 || true
  elif command -v python >/dev/null 2>&1; then
    python -m webbrowser "${OPEN_URL}" >/dev/null 2>&1 || true
  fi
fi

# Keep script alive while children run.
wait
