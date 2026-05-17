# Overlord

Supervisor service for multi-agent coding workflows. Resolves merge conflicts via Bedrock Sonnet, exposes APIs for IDE hooks (MCP / Claude Code), and includes a React dashboard.

## Setup

```bash
cd overlord
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # region + OVERLORD_MOCK_BEDROCK only; use aws login for creds
```

## Run backend

```bash
export OVERLORD_MOCK_BEDROCK=1   # or 0 for live Bedrock after aws login
cd backend && uvicorn main:app --reload --port 8000
```

- API docs: http://127.0.0.1:8000/docs
- Root `/` redirects to docs
- Health: http://127.0.0.1:8000/health

## Key endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/resolve` | Live conflict arbitration (IDE agents) |
| POST | `/resolve/demo/{name}` | Hackathon demo scenarios |
| POST | `/intents` | Record agent intent |
| POST | `/guardrails/check` | Pre-write check (agentic workflow; JSON body) |
| POST | `/guardrail/check` | Hackathon demo: proactive cache-delete scenario |
| GET | `/demo/smoke` | Run all three demo acts (mock Bedrock) |
| GET | `/scenarios` | List hardcoded scenario names |
| GET | `/conflicts` | List conflicts for dashboard |
| GET | `/conflicts/{id}` | Conflict detail |
| POST | `/conflicts/{id}/approve` | Human approve/reject |
| GET | `/history?session_id=` | Session event log |
| WS | `/ws/conflicts?session_id=` | Live conflict stream |

## AWS architecture (Memory + Policy)

| Layer | Service | Role |
|-------|---------|------|
| Session history | **AgentCore Memory** | Per-session agent actions, intents, decisions |
| Coordination rules | **AgentCore Policy** (Cedar) | Block file overlap, intent clashes, reversing peer work |
| Arbitration | **Bedrock Sonnet** (`invoke_model`) | Overlord resolves blocked actions |

Local defaults: `OVERLORD_USE_LOCAL_MEMORY=true` and `OVERLORD_USE_LOCAL_POLICY=true` (no AWS resources required for demo).

Cloud setup: **[`docs/AWS_SETUP.md`](docs/AWS_SETUP.md)** (full playbook) · [`infra/agentcore/README.md`](infra/agentcore/README.md) (console notes)

```bash
python scripts/bootstrap_agentcore.py      # create Memory + Policy Engine
python scripts/verify_aws_setup.py         # check creds + optional Bedrock/Memory
```

## Demo scenarios (three acts)

| Act | Scenario | How to run |
|-----|----------|------------|
| 1 | `merge_conflict` | `POST /resolve/demo/merge_conflict` |
| 2 | `intent_conflict` | `POST /resolve/demo/intent_conflict` |
| 3 | `guardrail_prevention` | `POST /guardrail/check` |

### Quick verify (mock Bedrock)

```bash
export OVERLORD_MOCK_BEDROCK=1
cd backend && uvicorn main:app --reload --port 8000
curl -s http://localhost:8000/demo/smoke | python3 -m json.tool
```

Expected: `"all_passed": true` and three checks with `"passed": true`.

## Live merge benchmark (Haiku vs Overlord)

Compares token usage when two Haiku agents thrash on a merge vs one Overlord arbitration call.

```bash
export OVERLORD_MOCK_BEDROCK=0
export OVERLORD_AGENT_MODEL_ID=us.anthropic.claude-haiku-4-5-20251001-v1:0
cd backend && uvicorn main:app --reload --port 8000
```

```bash
curl -s -X POST "http://127.0.0.1:8000/live/benchmark/merge_conflict?seed_mode=scenario" | python3 -m json.tool
```

Or: **Merge lab** → **Run live benchmark**. Use `seed_mode=scenario` for cheaper reproducible runs; `haiku` regenerates conflict code via Bedrock.

**Cost control:** `LIVE_BENCHMARK_DISABLED=1` blocks live calls.

## Deduplication benchmark (fleet)

Compares six agents on the commerce platform (overlapping auth + catalog work) vs one Overlord Sonnet call that continues one agent per cluster and reassigns the rest.

```bash
export OVERLORD_MOCK_BEDROCK=1   # or 0 for live Sonnet + Haiku
export LIVE_AGENT_MAX_TOKENS=4096
export LIVE_AGENT_REASSIGN_MAX_TOKENS=1024   # smaller patches for reassigned agents
python scripts/run_dedup_benchmark.py
# pairwise legacy: python scripts/run_dedup_benchmark.py --scenario duplicate_work
```

API: `POST /live/benchmark/dedup/duplicate_work_fleet`

Report: `overlord/experiments/results/dedup_report_<timestamp>.md`

Full write-up: [`experiments/EXPERIMENT_RESULTS.md`](experiments/EXPERIMENT_RESULTS.md)

## Merge conflict benchmark (baseline vs Overlord)

```bash
python scripts/run_live_benchmark.py --all --seed-mode scenario
```

Report: `overlord/experiments/results/merge_report_<scenario>_<timestamp>.md`

## Merge conflict fleet (6 agents, 4096 tokens)

Six agents with conflicting code on auth, catalog, and billing vs parallel per-file Overlord Sonnet merges.

```bash
export LIVE_AGENT_MAX_TOKENS=4096
export MERGE_FLEET_PARALLEL=1
export MERGE_FLEET_STRATEGY=haiku_chain
export MERGE_FLEET_ESCALATE_SONNET=0
python scripts/run_merge_fleet_benchmark.py
```

API: `POST /live/benchmark/merge-fleet/merge_conflict_fleet`

Report: `overlord/experiments/results/merge_fleet_report_<timestamp>.md`

## Guardrail benchmark (tiered Haiku / Sonnet)

Preflight is always local policy. LLM resolution uses **Haiku** for simple two-agent incidents and **Sonnet** for fleet (3+ agents), `intent_contradiction`, multi-file context, or large KB history.

```bash
export GUARDRAIL_STRATEGY=tiered   # tiered | haiku | sonnet
export GUARDRAIL_SONNET_MIN_AGENTS=3
python scripts/run_guardrail_benchmark.py
python scripts/run_guardrail_benchmark.py --fleet   # five-agent Sonnet path
```

API: `POST /guardrail/check` (pairwise demo)

Report: `overlord/experiments/results/guardrail_report_<timestamp>.json`

## Dashboard

```bash
cd frontend && npm install && npm run dev
```

Open http://localhost:5173 — proxies `/api` and `/ws` to the backend. Use **Merge lab** for heuristic compare and live Haiku vs Overlord benchmarks.

Requires Bedrock access to `us.anthropic.claude-sonnet-4-20250514-v1:0` in `us-east-1` when `OVERLORD_MOCK_BEDROCK` is unset.

## MCP (Cursor / Claude Code)

```bash
pip install mcp
cd overlord && python mcp/server.py
```

Add to Cursor MCP config (stdio): command `python`, args `mcp/server.py`, cwd `overlord/`.

Tools: `overlord_declare_intent`, `overlord_guardrail_check`, `overlord_resolve_conflict`, `overlord_get_history`.

## Claude Code hook

```bash
chmod +x integrations/claude-code/pre-write.sh
export OVERLORD_SESSION_ID=your_session
# Wire script in Claude Code PreToolUse for Write/Edit
```

## E2E demo

```bash
chmod +x scripts/e2e_agentic_demo.sh
OVERLORD_MOCK_BEDROCK=1 ./scripts/e2e_agentic_demo.sh
```

## Tests

```bash
pytest backend/tests -v
```
