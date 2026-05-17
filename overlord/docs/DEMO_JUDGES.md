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

## Act A2 — Gratitude handoff (blocked write)

After Act A, inspect the same guardrail response (or re-run the curl). Expect a `handoff` object:

```json
{
  "allowed": false,
  "handoff": {
    "owner_agent_id": "agent_a",
    "owner_intent": "...",
    "message": "Thanks for coordinating — agent_a is carrying `src/user.py` ...",
    "suggested_file_path": "app/billing/invoices.py"
  }
}
```

**Talking point:** Instead of a dead end, the blocked agent gets a polite redirect and optional backlog file.

## Act A3 — Auto intent alignment

```bash
curl -s -X POST "$OVERLORD_API_BASE/intents" -H 'Content-Type: application/json' -d '{
  "session_id": "mergeai-hackathon-demo",
  "agent_id": "agent_a",
  "file_path": "src/user.py",
  "intent": "maximum performance caching"
}'
curl -s -X POST "$OVERLORD_API_BASE/intents" -H 'Content-Type: application/json' -d '{
  "session_id": "mergeai-hackathon-demo",
  "agent_id": "agent_b",
  "file_path": "src/user.py",
  "intent": "minimize external dependencies"
}' | python3 -m json.tool
```

**Expected:** Second response has `"overlap_detected": true` and `alignment.unified_intent`. Check `inference_tier` when `OVERLORD_MOCK_BEDROCK=0`.

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

## Act C2 — Gratitude Ledger panel

Above **Missions (GitHub)**, the dashboard shows coordination stats: intents declared, guardrails blocked, alignments, dedup yields, tokens saved, and Haiku/Sonnet call counts. Run Acts A/A3/D to watch counters move.

## Act D — GitHub Issues delegation (missions)

**Server / one terminal:**

```bash
export OVERLORD_MOCK_BEDROCK=1   # or 0 for live Sonnet dedup
./scripts/demo_github_delegation.sh
```

**Talking point:** Two GitHub issues on the same file → Overlord delegates: one agent continues, one gets **`#103`** on `app/billing/invoices.py` via the Thanksgiving queue (not vague LLM text).

**Laptop A** (`OVERLORD_AGENT_ID=agent_a`):

```bash
export OVERLORD_AGENT_ID=agent_a
./scripts/demo_github_multi_machine.sh
```

**Laptop B** (`OVERLORD_AGENT_ID=agent_b`) — after A started:

```bash
export OVERLORD_AGENT_ID=agent_b
./scripts/demo_github_multi_machine.sh
```

**Dashboard:** Missions table shows `owner/repo#101` / `#102`, assigned agents, **Delegate all** / **Start**.

**Real GitHub (optional):** Label issue `overlord-ready` → webhook `POST /integrations/github/webhook` with `X-Hub-Signature-256`, or `POST /integrations/github/sync/42`.

## Architecture one-liner

> Shared **Overlord API** is the clerk; **AgentCore Runtime** is the judge. Every laptop’s subagent talks to the same clerk so guardrails and history stay in sync.
