#!/usr/bin/env bash
# Recreate helm/.venv with Python 3.10+ (required by bedrock-agentcore>=1.5.1).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PY=""
for candidate in python3.14 python3.13 python3.12 python3.11 python3; do
  if command -v "$candidate" >/dev/null 2>&1; then
    ver="$("$candidate" -c 'import sys; print(sys.version_info[:2])')"
    major="${ver#(}"
    major="${major%,*}"
    minor="${ver#*, }"
    minor="${minor%)*}"
    if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
      PY="$candidate"
      break
    fi
  fi
done

if [ -z "$PY" ]; then
  echo "ERROR: Need Python 3.10+. Install with: brew install python@3.11" >&2
  exit 1
fi

echo "Using $PY ($("$PY" --version))"
rm -rf .venv
"$PY" -m venv .venv
.venv/bin/pip install -U pip
.venv/bin/pip install -r requirements.txt
echo "OK: .venv ready. Run: source .venv/bin/activate"
