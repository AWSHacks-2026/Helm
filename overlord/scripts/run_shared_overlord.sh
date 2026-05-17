#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
set -a
# shellcheck disable=SC1091
source .env
set +a
export OVERLORD_USE_LOCAL_MEMORY="${OVERLORD_USE_LOCAL_MEMORY:-false}"
VENV="${ROOT}/.venv/bin/uvicorn"
if [ ! -x "$VENV" ]; then
  VENV="uvicorn"
fi
cd backend
exec "$VENV" main:app --host 0.0.0.0 --port "${PORT:-8000}"
