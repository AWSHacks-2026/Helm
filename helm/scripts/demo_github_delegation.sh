#!/usr/bin/env bash
set -euo pipefail
BASE="${HELM_API_BASE:?Set HELM_API_BASE to shared server URL}"
SESSION="${HELM_TEAM_SESSION:-mergeai-hackathon-demo}"
REPO="${GITHUB_REPO:-AWSHacks-2026/MergeAI}"

export GITHUB_MOCK=1

echo "=== Act D1: GitHub Issues missions (no real GitHub API) ==="
echo "API=$BASE SESSION=$SESSION REPO=$REPO"

curl -s -X POST "$BASE/missions" -H 'Content-Type: application/json' -d "{
  \"session_id\": \"$SESSION\",
  \"external_id\": \"${REPO}#101\",
  \"source\": \"github\",
  \"title\": \"JWT auth\",
  \"file_path\": \"src/user.py\"
}"
echo ""

curl -s -X POST "$BASE/missions" -H 'Content-Type: application/json' -d "{
  \"session_id\": \"$SESSION\",
  \"external_id\": \"${REPO}#102\",
  \"source\": \"github\",
  \"title\": \"JWT refresh\",
  \"file_path\": \"src/user.py\"
}"
echo ""

curl -s -X POST "$BASE/missions" -H 'Content-Type: application/json' -d "{
  \"session_id\": \"$SESSION\",
  \"external_id\": \"${REPO}#103\",
  \"source\": \"github\",
  \"title\": \"Billing invoices\",
  \"file_path\": \"app/billing/invoices.py\"
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
