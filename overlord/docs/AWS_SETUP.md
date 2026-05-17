# AWS setup for Overlord (hackathon playbook)

Overlord works **offline** with defaults (`OVERLORD_USE_LOCAL_MEMORY=true`, `OVERLORD_USE_LOCAL_POLICY=true`, `OVERLORD_MOCK_BEDROCK=1`). Use this guide when you want **real AWS** for judges, MCP agents, or multi-machine demos.

**Time budget:** ~2h minimum (Bedrock only) · ~6h recommended (Memory + Bedrock) · ~12–20h full story (Gateway + Policy ENFORCE)

---

## What agents actually use

| Path | AWS when enabled |
|------|------------------|
| **MCP** (`overlord/mcp/server.py`) → HTTP API | Same as backend env |
| `overlord_declare_intent` | `POST /intents` → **AgentCore Memory** (or local JSON) |
| `overlord_guardrail_check` | `POST /guardrails/check` → **Policy bridge** (+ Memory context) |
| `overlord_resolve_conflict` | `POST /resolve` → **Bedrock Sonnet** (unless mock) |
| Demo lab / `GET /demo/smoke` | Act 2 intent = **simulator** (no Bedrock); Acts 1 & 3 use Bedrock when mock off |

Flip cloud on by setting `overlord/.env` (copy from `.env.example`).

---

## Tier 0 — Credentials (15 min)

1. Install [AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html).
2. Log in (team hackathon account):

   ```bash
   aws login
   # or: aws configure
   export AWS_REGION=us-east-1
   ```

3. Verify:

   ```bash
   aws sts get-caller-identity
   cd overlord && source .venv/bin/activate
   python scripts/verify_aws_setup.py
   ```

**IAM (minimum):** `bedrock:InvokeModel`, `bedrock-agentcore:*` (or scoped Memory/Policy/Gateway), plus read for your account.

---

## Tier 1 — Live Bedrock arbitration (~2 h)

**Enables:** real merge resolution + guardrail Overlord verdicts (Acts 1 & 3).

1. **Model access:** Console → **Amazon Bedrock** → **Model access** → enable  
   `Anthropic Claude Sonnet 4.6` (`us.anthropic.claude-sonnet-4-6`) in **us-east-1**.

2. **`overlord/.env`:**

   ```bash
   AWS_REGION=us-east-1
   OVERLORD_MOCK_BEDROCK=0
   OVERLORD_USE_LOCAL_MEMORY=true
   OVERLORD_USE_LOCAL_POLICY=true
   ```

3. Run backend and smoke:

   ```bash
   cd overlord/backend && uvicorn main:app --reload --port 8000
   curl -s -X POST http://127.0.0.1:8000/resolve/demo/merge_conflict | python3 -m json.tool
   ```

4. **MCP agents:** point Cursor at the running API:

   ```json
   "env": { "OVERLORD_API_BASE": "http://127.0.0.1:8000" }
   ```

   (See `overlord/README.md` MCP section.)

**Verify:** `python scripts/verify_aws_setup.py --bedrock` should pass invoke probe.

---

## Tier 2 — AgentCore Memory (~3–4 h)

**Enables:** session history and retrieval in **AWS** (shared across laptops / AgentCore console).

### Option A — Script (fastest)

```bash
cd overlord && source .venv/bin/activate
export AWS_REGION=us-east-1
python scripts/bootstrap_agentcore.py --memory-only
# Prints AGENTCORE_MEMORY_ID=... — paste into .env
```

### Option B — Console

1. **Bedrock** → **AgentCore** → **Memory** → Create memory.
2. Copy **Memory ID** → `AGENTCORE_MEMORY_ID` in `.env`.

### `.env` for cloud memory

```bash
AGENTCORE_MEMORY_ID=<from bootstrap or console>
OVERLORD_USE_LOCAL_MEMORY=false
OVERLORD_USE_LOCAL_POLICY=true   # still local until Gateway (Tier 3)
OVERLORD_MOCK_BEDROCK=0
```

Restart uvicorn. MCP `overlord_declare_intent` + `overlord_get_history` now persist to AgentCore.

**Verify:**

```bash
python scripts/verify_aws_setup.py --memory
curl "http://127.0.0.1:8000/history?session_id=mcp-test"
```

---

## Tier 3 — Policy engine + Cedar (~4–6 h)

**Enables:** Cedar policies in AWS (upload + audit). **Runtime enforcement at Gateway** requires Tier 4.

### Bootstrap policy engine + upload Cedar

```bash
python scripts/bootstrap_agentcore.py --policy-only
# or full: python scripts/bootstrap_agentcore.py
```

Uploads statements from `backend/bedrock/policies/overlord_coordination.cedar`.

Set in `.env`:

```bash
AGENTCORE_POLICY_ENGINE_ID=<engine id>
OVERLORD_USE_LOCAL_POLICY=false
```

**Important:** Until **Gateway** is attached, Overlord still evaluates rules in Python (`agentcore_policy._evaluate_local`) using the same semantics as Cedar. Cloud engine holds the **governed copy** for judges; Gateway adds **ENFORCE at tool call**.

---

## Tier 4 — AgentCore Gateway (optional, ~8–12 h)

Native policy **ENFORCE** runs when agents call tools **through the Gateway**, not direct HTTP.

### Tools to expose

| Gateway tool name | Overlord backend |
|-------------------|------------------|
| `Overlord___declare_intent` | `POST /intents` |
| `Overlord___proposed_write` | `POST /guardrails/check` |
| `Overlord___resolve_conflict` | `POST /resolve` |

### CLI flow (AWS docs)

```bash
npm install -g @aws/agentcore
agentcore create --name OverlordGateway --defaults
cd OverlordGateway
# Add OpenAPI/HTTP target → your deployed Overlord URL (or ngrok for demo)
agentcore add gateway --name OverlordGW --authorizer-type NONE
agentcore add policy-engine --name OverlordPolicy --attach-to-gateways OverlordGW --attach-mode ENFORCE
agentcore add policy --name CoordinationRules --engine OverlordPolicy \
  --source ../backend/bedrock/policies/overlord_coordination.cedar
agentcore deploy
agentcore status   # gateway URL + ARNs
```

After deploy, update Cedar `resource` lines with the **gateway ARN** from `agentcore status` (wildcards are rejected).

Set `AGENTCORE_GATEWAY_ARN` in `.env` for documentation; point MCP/agents at Gateway MCP URL instead of raw FastAPI when ready.

See also: [`infra/agentcore/README.md`](../infra/agentcore/README.md).

---

## Recommended `.env` matrix

| Demo | `OVERLORD_MOCK_BEDROCK` | `USE_LOCAL_MEMORY` | `USE_LOCAL_POLICY` |
|------|-------------------------|--------------------|--------------------|
| Offline / CI | `1` | `true` | `true` |
| Live Sonnet only | `0` | `true` | `true` |
| Full cloud memory | `0` | `false` + `AGENTCORE_MEMORY_ID` | `true` |
| Full AWS story | `0` | `false` | `false` + `AGENTCORE_POLICY_ENGINE_ID` |

---

## End-to-end checklist (judges)

```bash
cd overlord && source .venv/bin/activate
cp .env.example .env   # fill IDs after bootstrap

# 1) Infra
python scripts/bootstrap_agentcore.py
python scripts/verify_aws_setup.py

# 2) Server
export OVERLORD_MOCK_BEDROCK=0
cd backend && uvicorn main:app --port 8000

# 3) Mock-off smoke (Acts 1 & 3 hit Bedrock; Act 2 simulator)
curl -s http://127.0.0.1:8000/demo/smoke | python3 -m json.tool

# 4) MCP agent session
# Cursor → overlord MCP with OVERLORD_API_BASE=http://127.0.0.1:8000
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `AccessDeniedException` on invoke | Enable model in Bedrock console; check region `us-east-1` |
| `ValidationException` model ID / inference profile | Use `us.anthropic.*` IDs in `.env` (e.g. Sonnet `us.anthropic.claude-sonnet-4-6`, Haiku `us.anthropic.claude-haiku-4-5-20251001-v1:0`). Raw `anthropic.*` IDs are auto-prefixed in code. |
| Memory writes fail | Set `AGENTCORE_MEMORY_ID`, `OVERLORD_USE_LOCAL_MEMORY=false` |
| Policy upload fails Cedar validation | Deploy Gateway first, put gateway ARN in `resource`; or use `validationMode=IGNORE_ALL_FINDINGS` in bootstrap script |
| MCP sees stale data | Same `session_id` across `declare_intent` / `guardrail_check` |
| Guardrail demo empty history | Demo uses session `guardrail-demo`; call `POST /guardrail/check` not raw check without seed |

---

## Clean up

Delete Memory, Policy Engine, and Gateway in console (or `agentcore remove` + `agentcore deploy`) to avoid hackathon charges.
