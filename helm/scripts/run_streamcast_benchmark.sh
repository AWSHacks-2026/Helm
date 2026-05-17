#!/usr/bin/env bash
# Orchestrate a Streamcast real-agent benchmark suite run.
set -euo pipefail

SUITE="${1:-}"
if [ -z "$SUITE" ] || { [ "$SUITE" != "independent" ] && [ "$SUITE" != "conflicting" ]; }; then
  echo "Usage: $0 <independent|conflicting>" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MERGEAI_ROOT="$(cd "$ROOT/.." && pwd)"
BENCHMARKS="$ROOT/benchmarks"
STREAMCAST="$MERGEAI_ROOT/streamcast"
MANIFEST="$BENCHMARKS/suites/$SUITE/manifest.yaml"
HELM_ENABLED="${HELM_ENABLED:-1}"
HELM_API_BASE="${HELM_API_BASE:-http://127.0.0.1:8000}"
WAIT_MODE="${WAIT_MODE:-prompt}"

if ! curl -sf "$HELM_API_BASE/health" >/dev/null; then
  echo "Helm API not healthy at $HELM_API_BASE — start ./scripts/run_shared_helm.sh" >&2
  exit 1
fi

SESSION_PREFIX="$(python3 -c "import yaml; print(yaml.safe_load(open('$MANIFEST'))['session_id_prefix'])")"
RUN_ID="$(date +%Y%m%d-%H%M%S)-$SUITE"
export HELM_TEAM_SESSION="${SESSION_PREFIX}-${RUN_ID}"
RESULTS_DIR="$BENCHMARKS/results"
RUN_DIR="$RESULTS_DIR/$RUN_ID"
mkdir -p "$RUN_DIR"

echo "Run ID: $RUN_ID"
echo "Suite: $SUITE"
echo "HELM_ENABLED=$HELM_ENABLED"
echo "Session: $HELM_TEAM_SESSION"

REPO_ROOT="$RUN_DIR/repo"
mkdir -p "$REPO_ROOT"
rsync -a --exclude '.benchmark-worktrees' --exclude '__pycache__' --exclude '.pytest_cache' \
  "$STREAMCAST/" "$REPO_ROOT/"

STARTED_AT="$(python3 -c 'import time; print(time.time())')"
WORKTREES_ROOT="$(cd "$ROOT" && PYTHONPATH="$ROOT" python3 -c "
from pathlib import Path
from benchmarks.git_worktree import prepare_run
from benchmarks.manifest import load_suite_manifest, Assignment
import sys

repo = Path(sys.argv[1])
run_id = sys.argv[2]
manifest = load_suite_manifest(Path(sys.argv[3]))
root = prepare_run(repo, run_id)
for a in manifest.assignments:
    from benchmarks.git_worktree import create_agent_worktree
    path = create_agent_worktree(root, a)
    print(f'{a.id}\t{path}')
" "$REPO_ROOT" "$RUN_ID" "$MANIFEST")"

echo ""
echo "Agent worktrees:"
while IFS=$'\t' read -r agent_id agent_path; do
  brief="$BENCHMARKS/suites/$SUITE/agents/${agent_id}.md"
  echo "  - $agent_id"
  echo "    Worktree: $agent_path"
  echo "    Brief:    $brief"
  echo "    Open Cursor at worktree with the brief as prompt."
  if [ "$WAIT_MODE" = "file" ]; then
    done_file="$agent_path/.done"
    echo "    Waiting for $done_file ..."
    while [ ! -f "$done_file" ]; do sleep 2; done
  else
    read -r -p "    Press Enter when $agent_id is finished..."
  fi
done <<< "$WORKTREES_ROOT"

BRANCHES="$(python3 -c "import yaml; m=yaml.safe_load(open('$MANIFEST')); print(' '.join(a['branch'] for a in m['assignments']))")"
MERGE_JSON="$(cd "$ROOT" && PYTHONPATH="$ROOT" python3 -c "
from pathlib import Path
from benchmarks.git_worktree import merge_branches
import json, sys
branches = sys.argv[1].split()
root = Path(sys.argv[2]) / '.benchmark-worktrees' / sys.argv[3]
result = merge_branches(root, branches)
print(json.dumps({'success': result.success, 'conflict_files': result.conflict_files, 'merge_commit': result.merge_commit}))
" "$BRANCHES" "$REPO_ROOT" "$RUN_ID")"

MERGE_SUCCESS="$(echo "$MERGE_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["success"])')"
CONFLICT_COUNT="$(echo "$MERGE_JSON" | python3 -c 'import json,sys; print(len(json.load(sys.stdin)["conflict_files"]))')"

if [ "$MERGE_SUCCESS" != "True" ] && [ "$HELM_ENABLED" = "1" ]; then
  echo ""
  echo "Merge conflicts detected. Resolve via Helm:"
  echo "  - MCP: helm_resolve_conflict"
  echo "  - API: POST $HELM_API_BASE/integrations/git/merge-conflict"
  echo "$MERGE_JSON" | python3 -m json.tool
fi

ENDED_AT="$(python3 -c 'import time; print(time.time())')"
cat > "$RUN_DIR/meta.json" <<EOF
{
  "run_id": "$RUN_ID",
  "suite": "$SUITE",
  "helm_enabled": $([ "$HELM_ENABLED" = "1" ] && echo true || echo false),
  "session_id": "$HELM_TEAM_SESSION",
  "started_at": $STARTED_AT,
  "ended_at": $ENDED_AT,
  "merge_success": $([ "$MERGE_SUCCESS" = "True" ] && echo true || echo false),
  "git_conflict_files": $CONFLICT_COUNT,
  "repo_root": "$REPO_ROOT"
}
EOF

echo ""
echo "Run metadata: $RUN_DIR/meta.json"
echo "Collect: python scripts/collect_streamcast_run.py --run-id $RUN_ID"
