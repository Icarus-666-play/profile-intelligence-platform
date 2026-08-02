#!/usr/bin/env bash
# Compatibility wrapper — prefer ./scripts/start.sh
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/scripts/start.sh" "$@"
