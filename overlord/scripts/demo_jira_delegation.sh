#!/usr/bin/env bash
set -euo pipefail
BASE="${OVERLORD_API_BASE:?Set OVERLORD_API_BASE to shared server URL}"
SESSION="${OVERLORD_TEAM_SESSION:-mergeai-hackathon-demo}"

export JIRA_MOCK=1

echo "=== Act D1: Jira-style missions (no real Jira) ==="
echo "API=$BASE SESSION=$SESSION"

curl -s -X POST "$BASE/missions" -H 'Content-Type: application/json' -d "{
  \"session_id\": \"$SESSION\",
  \"external_id\": \"PROJ-101\",
  \"source\": \"jira\",
  \"title\": \"JWT auth\",
  \"file_path\": \"src/user.py\"
}"
echo ""

curl -s -X POST "$BASE/missions" -H 'Content-Type: application/json' -d "{
  \"session_id\": \"$SESSION\",
  \"external_id\": \"PROJ-102\",
  \"source\": \"jira\",
  \"title\": \"JWT refresh\",
  \"file_path\": \"src/user.py\"
}"
echo ""

echo "=== Act D2: Delegate (dedup overlapping file) ==="
curl -s -X POST "$BASE/missions/delegate" -H 'Content-Type: application/json' -d "{
  \"session_id\": \"$SESSION\",
  \"use_llm_dedup\": true
}" | python3 -m json.tool

echo ""
echo "Missions:"
curl -s "$BASE/missions?session_id=$SESSION" | python3 -m json.tool
