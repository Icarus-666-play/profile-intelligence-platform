#!/usr/bin/env bash
# Build the React SPA into src/profile_intelligence/web/dist.
#
#   ./scripts/build-ui.sh

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/frontend"

if ! command -v npm >/dev/null 2>&1; then
  echo "npm not found. Install Node.js first." >&2
  exit 1
fi

echo "Installing frontend dependencies…"
npm install

echo "Building production UI…"
npm run build

echo "Built SPA → src/profile_intelligence/web/dist/"
