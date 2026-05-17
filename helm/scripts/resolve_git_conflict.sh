#!/usr/bin/env bash
set -euo pipefail
FILE="${1:?usage: resolve_git_conflict.sh <file-with-conflict-markers>}"
BASE="${HELM_API_BASE:-http://127.0.0.1:8000}"
SESSION="${HELM_TEAM_SESSION:-mergeai-hackathon-demo}"

python3 - "$FILE" "$BASE" "$SESSION" <<'PY'
import json
import sys
import urllib.request

path, base, session = sys.argv[1:4]
text = open(path, encoding="utf-8").read()
if "<<<<<<<" not in text:
    raise SystemExit("No conflict markers in file")

parts = text.split("<<<<<<<", 1)[1]
ours, rest = parts.split("=======", 1)
ours = ours.split("\n", 1)[-1]
theirs, _rest = rest.split(">>>>>>>", 1)
theirs = theirs.rsplit("\n", 1)[0]

body = json.dumps(
    {
        "session_id": session,
        "file_path": path,
        "ours": ours.strip(),
        "theirs": theirs.strip(),
    }
).encode()

req = urllib.request.Request(
    f"{base.rstrip('/')}/integrations/git/merge-conflict",
    data=body,
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req, timeout=120) as resp:
    print(json.dumps(json.load(resp), indent=2))
PY
