# Judge demo script (5 minutes)

**Visual story:** Helm (nav wheel) steers the fleet; **Gratitude** tab shows time/tokens returned — green metrics, calm white UI.

## Build with Gratitude — open here (30 seconds)

**Theme is the product, not the slide deck.** Our parents spent careers in software engineering watching hours vanish to merge conflicts, agents stepping on each other, and wasted compute. **Overlord** (Helm coordination + Amazon Bedrock) is our thank-you: every blocked write and deduped mission is **time back** for someone still in the chair.

**Show the Gratitude tab** — the ledger is load-bearing. You cannot swap “wellness” for this theme without losing the point.

**Presenter arc:** `?presenter=1` → Begin presentation → Control Tower replay → Incidents → **Gratitude** → Results charts.

**Deep dive (optional):** **Under the hood** (`?view=recorder`) — N=2 agents + Helm with a scrubbable timeline, file snippets, and dedup/merge/guardrail steps.

---

## Prerequisites

1. **Shared Helm API** running (one laptop or Docker):

   ```bash
   cd helm && ./scripts/run_shared_helm.sh
   # or expose via ngrok: ngrok http 8000
   ```

2. **`.env` on server** — cloud memory + AgentCore runtime:

   ```bash
   HELM_TEAM_SESSION=mergeai-hackathon-demo
   AGENTCORE_MEMORY_ID=<from bootstrap>
   HELM_USE_LOCAL_MEMORY=false
   HELM_ARBITRATOR_ARN=<runtime arn>
   HELM_MOCK_BEDROCK=0
   ```

3. **Each demo laptop** — MCP or curl:

   ```bash
   export HELM_API_BASE=https://YOUR-SHARED-HOST
   export HELM_TEAM_SESSION=mergeai-hackathon-demo
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
export HELM_API_BASE=...
export HELM_TEAM_SESSION=mergeai-hackathon-demo
curl -s -X POST "$HELM_API_BASE/guardrails/check" -H 'Content-Type: application/json' -d '{
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
curl -s -X POST "$HELM_API_BASE/intents" -H 'Content-Type: application/json' -d '{
  "session_id": "mergeai-hackathon-demo",
  "agent_id": "agent_a",
  "file_path": "src/user.py",
  "intent": "maximum performance caching"
}'
curl -s -X POST "$HELM_API_BASE/intents" -H 'Content-Type: application/json' -d '{
  "session_id": "mergeai-hackathon-demo",
  "agent_id": "agent_b",
  "file_path": "src/user.py",
  "intent": "minimize external dependencies"
}' | python3 -m json.tool
```

**Expected:** Second response has `"overlap_detected": true` and `alignment.unified_intent`. Check `inference_tier` when `HELM_MOCK_BEDROCK=0`.

## Act B — Git merge conflict

```bash
export HELM_API_BASE=...
./scripts/resolve_git_conflict.sh demo/fixtures/conflicted_user.py
```

**Expected:** JSON with `resolution.resolved_code` from Bedrock AgentCore.

**Optional CI story:** GitHub → Actions → **Helm merge conflict demo** (requires repo secret `HELM_API_BASE`).

## Act C — Control Tower (recommended judge path)

**Terminals:**

```bash
# Terminal 1
cd helm && source .venv/bin/activate && cd backend && uvicorn main:app --reload --port 8000
# or: ./scripts/run_shared_helm.sh

# Terminal 2
cd helm/frontend && npm run dev
```

**Browser:** http://127.0.0.1:5173/?presenter=1

1. Click **Begin presentation** (guided walkthrough).
2. Watch ShopFix replay — dedup on `auth.py`, guardrail block.
3. **Incidents** — duplicate work our parents lived through.
4. **Gratitude** — theme on screen: blocked, deduped, tokens returned (say the parent line here).
5. **Results** — pillar headlines + chart deck (← → in presenter mode).
6. Optional: **Run live guardrail (AWS)** on Results (`POST /guardrail/check`) only if AWS is verified.

**Fallback if AWS fails:** replay + static charts only — do not click live benchmark buttons on stage.

**ShopFix storefront (optional):** http://127.0.0.1:8001 — set `VITE_SHOPFIX_URL` in `frontend/.env`.

## Act C (legacy) — Dashboard + curl history

Open http://localhost:5173 — session `mergeai-hackathon-demo` shows history from Acts A/B.

## Act C2 — Gratitude Ledger panel

Above **Missions (GitHub)**, the dashboard shows coordination stats: intents declared, guardrails blocked, alignments, dedup yields, tokens saved, and Haiku/Sonnet call counts. Run Acts A/A3/D to watch counters move.

## Act D — GitHub Issues delegation (missions)

**Server / one terminal:**

```bash
export HELM_MOCK_BEDROCK=1   # or 0 for live Sonnet dedup
./scripts/demo_github_delegation.sh
```

**Talking point:** Two GitHub issues on the same file → Helm delegates: one agent continues, one gets **`#103`** on `app/billing/invoices.py` via the Thanksgiving queue (not vague LLM text).

**Laptop A** (`HELM_AGENT_ID=agent_a`):

```bash
export HELM_AGENT_ID=agent_a
./scripts/demo_github_multi_machine.sh
```

**Laptop B** (`HELM_AGENT_ID=agent_b`) — after A started:

```bash
export HELM_AGENT_ID=agent_b
./scripts/demo_github_multi_machine.sh
```

**Dashboard:** Missions table shows `owner/repo#101` / `#102`, assigned agents, **Delegate all** / **Start**.

**Real GitHub (optional):** Label issue `helm-ready` → webhook `POST /integrations/github/webhook` with `X-Hub-Signature-256`, or `POST /integrations/github/sync/42`.

## Architecture one-liner

> Shared **Helm API** is the clerk; **AgentCore Runtime** is the judge. Every laptop’s subagent talks to the same clerk so guardrails and history stay in sync.
