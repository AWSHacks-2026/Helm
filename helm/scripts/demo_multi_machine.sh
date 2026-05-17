#!/usr/bin/env bash
set -euo pipefail
BASE="${HELM_API_BASE:?Set HELM_API_BASE to shared server URL}"
SESSION="${HELM_TEAM_SESSION:-mergeai-hackathon-demo}"
FILE="src/user.py"

echo "=== Act A: Multi-machine guardrails ==="
echo "API=$BASE SESSION=$SESSION"

echo "[Laptop A] agent_a declares intent..."
curl -s -X POST "$BASE/intents" -H 'Content-Type: application/json' -d "{
  \"session_id\": \"$SESSION\",
  \"agent_id\": \"agent_a\",
  \"file_path\": \"$FILE\",
  \"intent\": \"Add caching to get_user\"
}"
echo ""

echo "[Laptop B] agent_b blocked on write..."
curl -s -X POST "$BASE/guardrails/check" -H 'Content-Type: application/json' -d "{
  \"session_id\": \"$SESSION\",
  \"agent_id\": \"agent_b\",
  \"file_path\": \"$FILE\",
  \"action\": \"write\",
  \"proposed_code\": \"def get_user(user_id: str) -> User: return db.query(user_id)\"
}" | python3 -m json.tool

echo ""
echo "History:"
curl -s "$BASE/history?session_id=$SESSION" | python3 -m json.tool | head -40
