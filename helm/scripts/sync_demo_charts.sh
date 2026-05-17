#!/usr/bin/env bash
# Copy presentation PNGs into the Helm frontend public folder.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${ROOT}/experiments/charts"
DEST="${ROOT}/frontend/public/demo-charts"

CHARTS=(
  00_dashboard.png
  01_contention_savings.png
  03_contention_agents.png
  04_merge_fleet_wall.png
  09_guardrail_headline.png
)

mkdir -p "${DEST}"
for name in "${CHARTS[@]}"; do
  cp "${SRC}/${name}" "${DEST}/${name}"
done

echo "Synced ${#CHARTS[@]} charts to ${DEST}"
