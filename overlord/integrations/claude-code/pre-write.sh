#!/usr/bin/env bash
# Claude Code PreToolUse hook — call Overlord guardrails before Write/Edit
set -euo pipefail

FILE_PATH="${FILE_PATH:-}"
AGENT_ID="${CLAUDE_AGENT_ID:-claude-code}"
SESSION_ID="${OVERLORD_SESSION_ID:-default}"
BASE="${OVERLORD_API_BASE:-http://127.0.0.1:8000}"

payload=$(jq -n \
  --arg session_id "$SESSION_ID" \
  --arg agent_id "$AGENT_ID" \
  --arg file_path "$FILE_PATH" \
  --arg proposed_code "${TOOL_INPUT:-}" \
  '{session_id: $session_id, agent_id: $agent_id, file_path: $file_path, action: "write", proposed_code: $proposed_code}')

result=$(curl -s -X POST "$BASE/guardrails/check" \
  -H "Content-Type: application/json" \
  -d "$payload")

allowed=$(echo "$result" | jq -r '.allowed')
if [ "$allowed" = "false" ]; then
  echo "Overlord blocked write: $(echo "$result" | jq -r '.reason')" >&2
  exit 2
fi
exit 0
