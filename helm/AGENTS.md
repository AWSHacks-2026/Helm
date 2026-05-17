# Helm — Cursor guide for teammates

Branch: **`feature/contention-gated-coordination`** (push before testing).

This branch adds a **contention gate** so Helm skips expensive Bedrock coordination when agents are not actually colliding. **Guardrails** are a separate layer (pre-write policy). Both can run on the same session.

---

## Quick start (local, no AWS)

```bash
cd helm
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt pyyaml
cp .env.example .env

export HELM_MOCK_BEDROCK=1
export HELM_GATE_ENABLED=1
export HELM_USE_LOCAL_MEMORY=true
export HELM_USE_LOCAL_POLICY=true

cd backend && uvicorn main:app --reload --port 8000
```

**Tests (full suite):**

```bash
cd helm && source .venv/bin/activate
HELM_MOCK_BEDROCK=1 pytest -q
```

**ShopFix-only tests:**

```bash
HELM_MOCK_BEDROCK=1 pytest -q backend/tests/agents/ backend/tests/bedrock/test_contention_gate.py
```

---

## Contention gate vs guardrails

| Layer | When it runs | What it does | Main code |
|-------|----------------|--------------|-----------|
| **Contention gate** | Before dedup / intent alignment / fleet coordination | Cheap check: file clusters, intent overlap, contradictions. Tier `allow` → **no Sonnet dedup**. Tier `arbitrate` → full Helm. | `backend/bedrock/contention_gate.py` |
| **Guardrails** | Before an agent writes a file (`POST /guardrails/check`) | Policy + optional Sonnet: block unsafe or conflicting writes, gratitude handoff | `backend/routes/guardrails.py`, `backend/bedrock/agentcore_policy.py` |

They compose:

1. Agent declares intent → `POST /intents` → gate may return `contention.gate_tier: "allow"` (skip align Bedrock).
2. Agent proposes write → `POST /guardrails/check` → may block even when gate allowed dedup skip.

Do not conflate them in demos: **gate = coordination cost**; **guardrail = write safety**.

---

## Contention gate behavior

**Env vars** (see `.env.example`):

| Variable | Default | Meaning |
|----------|---------|---------|
| `HELM_GATE_ENABLED` | `1` | Master switch |
| `HELM_GATE_FORCE` | `0` | `1` = always arbitrate (legacy benchmarks) |
| `HELM_GATE_MIN_AGENTS` | `2` | Min agents on same file to form a cluster |
| `HELM_GATE_INTENT_OVERLAP` | `0.35` | Jaccard threshold on intent tokens |
| `HELM_GATE_FAIL_MODE` | `open` | `closed` + `HELM_GATE_TRIAGE=1` for prefix-overlap triage |
| `HELM_GATE_LOG_SKIPS` | `1` | Log `allow` tier to knowledge base as `contention_gate` events |

**Tiers:** `allow` | `triage` | `arbitrate`

**Dedup path** (`assess_dedup`): groups agents by `file_path` in `SessionStore`. No cluster ≥ `HELM_GATE_MIN_AGENTS` → `allow` (skip `detect_duplication*`).

**Intent path** (`assess_intent`): peers on same file; overlap / contradiction → `arbitrate`.

**API:** `POST /intents` response includes:

```json
{
  "recorded": true,
  "overlap_detected": false,
  "alignment": null,
  "contention": {
    "contention_detected": false,
    "gate_tier": "allow",
    "contention_kind": null,
    "signals": [],
    "peers": [],
    "coordination_recommended": false
  }
}
```

**Wired into:** `dedup_harness.py`, `services/delegation.py`, `services/intent_alignment.py`, ShopFix harness.

---

## Guardrails (unchanged contract)

```bash
curl -s -X POST http://127.0.0.1:8000/guardrails/check \
  -H 'Content-Type: application/json' \
  -d '{
    "session_id": "demo-session",
    "agent_id": "agent_a",
    "file_path": "app/cache.py",
    "proposed_action": "delete Redis cache keys"
  }' | python3 -m json.tool
```

Demo act: `POST /guardrail/check` (hackathon scenario). Benchmark: `python scripts/run_guardrail_benchmark.py`.

With contention gate on, guardrails still run on every proposed write; gate does not replace them.

---

## ShopFix git benchmark (this branch)

Etsy-lite fixture for **real git + optional real Bedrock** metrics:

| Script | Bedrock | Purpose |
|--------|---------|---------|
| `scripts/run_shopfix_benchmark.py --mock` | Mock | CI-friendly; needs Helm API on `:8000` |
| `scripts/run_shopfix_live_benchmark.py` | Live | Real USD; refuses mock unless `--allow-mock` |

Docs: `experiments/SHOPFIX_BENCHMARK.md`, `experiments/SHOPFIX_LIVE_RESULTS.md`.

```bash
# ShopFix app alone (teammate demo can use another port)
cd fixtures/shopfix/backend && python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && python scripts/seed.py
uvicorn app.main:app --port 8001
```

If your teammate’s demo uses a different app or port, only share **`HELM_*` on :8000** — ShopFix is optional for gate/guardrail testing.

---

## Scenarios to try

| Name | What it proves |
|------|----------------|
| `commerce_disjoint` | 6 agents, 6 files → gate `allow`, 0 dedup Bedrock calls (mock harness) |
| `duplicate_work_fleet` | Overlap → gate `arbitrate`, Sonnet fleet dedup |
| ShopFix `disjoint` / `contention` | Real git + pytest gate (`run_shopfix_*`) |

```bash
HELM_MOCK_BEDROCK=1 HELM_GATE_ENABLED=1 python scripts/run_dedup_benchmark.py --scenario commerce_disjoint
```

---

## Key files (edit map)

```
backend/bedrock/contention_gate.py   # gate logic
backend/bedrock/intent_overlap.py    # overlap + contradiction helpers
backend/services/intent_alignment.py # POST /intents alignment + contention payload
backend/agents/dedup_harness.py      # fleet dedup benchmark + gate
backend/store/sessions.py            # file_clusters(), intents_on_file()
fixtures/shopfix/                    # Etsy clone benchmark repo
backend/tests/bedrock/test_contention_gate.py
```

---

## Live AWS (when ready)

```bash
export HELM_MOCK_BEDROCK=0 AWS_DEFAULT_REGION=us-east-1
python scripts/verify_aws_setup.py --bedrock
```

See `docs/AWS_SETUP.md` and `docs/DEMO_JUDGES.md` for multi-machine demos.

---

## Parallel work with teammate

- Use the **same branch** after `git pull origin feature/contention-gated-coordination`.
- Coordinate **session_id** if testing guardrails + intents together on shared Helm API.
- Contention gate tests do not require ShopFix; guardrail tests do not require ShopFix.
- Avoid committing `helm/experiments/results/`, `.venv`, `fixtures/shopfix/**/.venv`, `node_modules/`.
