#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"
PYTHON="${PYTHON:-python3.11}"
if ! command -v "$PYTHON" >/dev/null 2>&1; then
  PYTHON=python3
fi
"$PYTHON" -m venv .venv
source .venv/bin/activate
pip install -q -r requirements.txt
pytest -q
if [ -f "$ROOT/frontend/package.json" ]; then
  cd "$ROOT/frontend"
  npm ci
  npm run build
fi
echo "ShopFix verify OK"
