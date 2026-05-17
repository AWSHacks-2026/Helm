#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

source .venv/bin/activate 2>/dev/null || true

: "${HELM_ARBITRATOR_ARN:?Set HELM_ARBITRATOR_ARN in helm/.env}"
: "${AWS_DEFAULT_REGION:=us-east-1}"

SESSION_ID="smoke-$(uuidgen | tr '[:upper:]' '[:lower:]')"

python - <<PY
import json
import os
import sys

sys.path.insert(0, "backend")
from bedrock.agentcore_client import invoke_arbitrator

result = invoke_arbitrator(
    agent_runtime_arn=os.environ["HELM_ARBITRATOR_ARN"],
    session_id="${SESSION_ID}",
    agent_a={"intent": "cache lookups", "code": "def get_user(user_id):\\n    return db.query(user_id)"},
    agent_b={"intent": "add return type", "code": "def get_user(user_id: str) -> User:\\n    return db.query(user_id)"},
    kb_context=None,
)
print(json.dumps(result, indent=2))
assert result["conflict_type"] == "merge_conflict"
print("SMOKE OK")
PY
