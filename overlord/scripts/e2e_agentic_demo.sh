#!/usr/bin/env bash
set -euo pipefail

SESSION="demo_sess_$(date +%s)"
BASE="${OVERLORD_API_BASE:-http://127.0.0.1:8000}"

echo "Session: $SESSION"

curl -s -X POST "$BASE/intents" -H 'Content-Type: application/json' -d "{
  \"session_id\": \"$SESSION\",
  \"agent_id\": \"agent_a\",
  \"file_path\": \"src/user.py\",
  \"intent\": \"Add caching to get_user\"
}"

echo ""

curl -s -X POST "$BASE/intents" -H 'Content-Type: application/json' -d "{
  \"session_id\": \"$SESSION\",
  \"agent_id\": \"agent_b\",
  \"file_path\": \"src/user.py\",
  \"intent\": \"Add type hints to get_user\"
}"

echo ""

curl -s -X POST "$BASE/guardrails/check" -H 'Content-Type: application/json' -d "{
  \"session_id\": \"$SESSION\",
  \"agent_id\": \"agent_b\",
  \"file_path\": \"src/user.py\",
  \"action\": \"write\",
  \"proposed_code\": \"def get_user(user_id: str) -> User: return db.query(user_id)\"
}" | python3 -m json.tool

echo ""

curl -s -X POST "$BASE/resolve" -H 'Content-Type: application/json' -d "{
  \"session_id\": \"$SESSION\",
  \"file_path\": \"src/user.py\",
  \"agent_a\": {\"agent_id\": \"agent_a\", \"intent\": \"caching\", \"code\": \"def get_user(user_id): ...\"},
  \"agent_b\": {\"agent_id\": \"agent_b\", \"intent\": \"types\", \"code\": \"def get_user(user_id: str) -> User: ...\"}
}" | python3 -m json.tool

echo ""

curl -s "$BASE/history?session_id=$SESSION" | python3 -m json.tool
