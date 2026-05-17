#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [ -d .git ]; then
  echo "Golden repo already initialized"
  exit 0
fi
git init -b main
git add .
git commit -m "chore: ShopFix golden baseline"
echo "Golden commit: $(git rev-parse HEAD)"
