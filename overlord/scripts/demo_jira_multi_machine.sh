#!/usr/bin/env bash
set -euo pipefail
BASE="${OVERLORD_API_BASE:?Set OVERLORD_API_BASE}"
SESSION="${OVERLORD_TEAM_SESSION:-mergeai-hackathon-demo}"
AGENT="${OVERLORD_AGENT_ID:?Set OVERLORD_AGENT_ID (agent_a or agent_b)}"
FILE="${OVERLORD_DEMO_FILE:-src/user.py}"

echo "=== Act D3: Multi-laptop mission start + guardrails ==="
echo "API=$BASE SESSION=$SESSION AGENT=$AGENT"

MISSION_ID="$(curl -s "$BASE/missions?session_id=$SESSION" | python3 -c "
import json,sys,os
agent=os.environ.get('AGENT','')
for m in json.load(sys.stdin):
    if m.get('assigned_agent_id')==agent:
        print(m['mission_id']); break
")"

if [[ -z "$MISSION_ID" ]]; then
  echo "No mission assigned to $AGENT — run demo_jira_delegation.sh first"
  exit 1
fi

echo "Starting mission $MISSION_ID as $AGENT..."
curl -s -X POST "$BASE/missions/$MISSION_ID/start?session_id=$SESSION" \
  -H 'Content-Type: application/json' \
  -d "{\"agent_id\": \"$AGENT\"}" | python3 -m json.tool

if [[ "$AGENT" == "agent_b" ]]; then
  echo ""
  echo "agent_b write attempt (expect block if agent_a started first on same file):"
  curl -s -X POST "$BASE/guardrails/check" -H 'Content-Type: application/json' -d "{
    \"session_id\": \"$SESSION\",
    \"agent_id\": \"agent_b\",
    \"file_path\": \"$FILE\",
    \"action\": \"write\",
    \"proposed_code\": \"def get_user(user_id: str) -> User: return db.query(user_id)\"
  }" | python3 -m json.tool
fi
