# Judge demo script (5 minutes)

## Prerequisites

1. **Shared Overlord API** running (one laptop or Docker):

   ```bash
   cd overlord && ./scripts/run_shared_overlord.sh
   # or expose via ngrok: ngrok http 8000
   ```

2. **`.env` on server** — cloud memory + AgentCore runtime:

   ```bash
   OVERLORD_TEAM_SESSION=mergeai-hackathon-demo
   AGENTCORE_MEMORY_ID=<from bootstrap>
   OVERLORD_USE_LOCAL_MEMORY=false
   OVERLORD_ARBITRATOR_ARN=<runtime arn>
   OVERLORD_MOCK_BEDROCK=0
   ```

3. **Each demo laptop** — MCP or curl:

   ```bash
   export OVERLORD_API_BASE=https://YOUR-SHARED-HOST
   export OVERLORD_TEAM_SESSION=mergeai-hackathon-demo
   ```

## Act A — Live guardrails (multi-machine)

**Laptop A:**

```bash
./scripts/demo_multi_machine.sh
# Stop after intent line, or run full script from B only for guardrail half
```

**Talking point:** Agent A declared intent on `src/user.py` in **shared AgentCore Memory**.

**Laptop B:**

```bash
export OVERLORD_API_BASE=...
export OVERLORD_TEAM_SESSION=mergeai-hackathon-demo
curl -s -X POST "$OVERLORD_API_BASE/guardrails/check" -H 'Content-Type: application/json' -d '{
  "session_id": "mergeai-hackathon-demo",
  "agent_id": "agent_b",
  "file_path": "src/user.py",
  "action": "write",
  "proposed_code": "def get_user(user_id: str) -> User: return db.query(user_id)"
}' | python3 -m json.tool
```

**Expected:** `"allowed": false` — Agent B blocked because Agent A already owns the file.

## Act B — Git merge conflict

```bash
export OVERLORD_API_BASE=...
./scripts/resolve_git_conflict.sh demo/fixtures/conflicted_user.py
```

**Expected:** JSON with `resolution.resolved_code` from Bedrock AgentCore.

**Optional CI story:** GitHub → Actions → **Overlord merge conflict demo** (requires repo secret `OVERLORD_API_BASE`).

## Act C — Dashboard

```bash
cd frontend && npm run dev
```

Open http://localhost:5173 — session `mergeai-hackathon-demo` shows history from Acts A/B.

## Act D — Jira delegation (missions)

**Server / one terminal:**

```bash
export OVERLORD_MOCK_BEDROCK=1   # or 0 for live Sonnet dedup
./scripts/demo_jira_delegation.sh
```

**Talking point:** Two Jira tickets on the same file → Overlord delegates: one agent continues, one gets a reassigned task (token savings).

**Laptop A** (`OVERLORD_AGENT_ID=agent_a`):

```bash
export OVERLORD_AGENT_ID=agent_a
./scripts/demo_jira_multi_machine.sh
```

**Laptop B** (`OVERLORD_AGENT_ID=agent_b`) — after A started:

```bash
export OVERLORD_AGENT_ID=agent_b
./scripts/demo_jira_multi_machine.sh
```

**Dashboard:** Missions table shows `PROJ-101` / `PROJ-102`, assigned agents, **Delegate all** / **Start**.

**Real Jira (optional):** Label issue `overlord-ready` → webhook `POST /integrations/jira/webhook` with header `X-Overlord-Secret`, or `POST /integrations/jira/sync/PROJ-123`.

## Architecture one-liner

> Shared **Overlord API** is the clerk; **AgentCore Runtime** is the judge. Every laptop’s subagent talks to the same clerk so guardrails and history stay in sync.
