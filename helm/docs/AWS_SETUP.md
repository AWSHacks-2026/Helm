# AWS setup for Helm (hackathon playbook)

Helm works **offline** with defaults (`HELM_USE_LOCAL_MEMORY=true`, `HELM_USE_LOCAL_POLICY=true`, `HELM_MOCK_BEDROCK=1`). Use this guide when you want **real AWS** for judges, MCP agents, or multi-machine demos.

**Time budget:** ~2h minimum (Bedrock only) · ~6h recommended (Memory + Bedrock) · ~12–20h full story (Gateway + Policy ENFORCE)

---

## What agents actually use

| Path | AWS when enabled |
|------|------------------|
| **MCP** (`helm/mcp/server.py`) → HTTP API | Same as backend env |
| `helm_declare_intent` | `POST /intents` → **AgentCore Memory** (or local JSON) |
| `helm_guardrail_check` | `POST /guardrails/check` → **Policy bridge** (+ Memory context) |
| `helm_resolve_conflict` | `POST /resolve` → **Bedrock Sonnet** (unless mock) |
| Demo lab / `GET /demo/smoke` | Act 2 intent = **simulator** (no Bedrock); Acts 1 & 3 use Bedrock when mock off |

Flip cloud on by setting `helm/.env` (copy from `.env.example`).

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
   cd helm && source .venv/bin/activate
   python scripts/verify_aws_setup.py
   ```

**IAM (minimum):** `bedrock:InvokeModel`, `bedrock-agentcore:*` (or scoped Memory/Policy/Gateway), plus read for your account.

---

## Tier 1 — Live Bedrock arbitration (~2 h)

**Enables:** real merge resolution + guardrail Helm verdicts (Acts 1 & 3).

1. **Model access:** Console → **Amazon Bedrock** → **Model access** → enable  
   `Anthropic Claude Sonnet 4.6` (`us.anthropic.claude-sonnet-4-6`) in **us-east-1**.

2. **`helm/.env`:**

   ```bash
   AWS_REGION=us-east-1
   HELM_MOCK_BEDROCK=0
   HELM_USE_LOCAL_MEMORY=true
   HELM_USE_LOCAL_POLICY=true
   ```

3. Run backend and smoke:

   ```bash
   cd helm/backend && uvicorn main:app --reload --port 8000
   curl -s -X POST http://127.0.0.1:8000/resolve/demo/merge_conflict | python3 -m json.tool
   ```

4. **MCP agents:** point Cursor at the running API:

   ```json
   "env": { "HELM_API_BASE": "http://127.0.0.1:8000" }
   ```

   (See `helm/README.md` MCP section.)

**Verify:** `python scripts/verify_aws_setup.py --bedrock` should pass invoke probe.

---

## Tier 2 — AgentCore Memory (~3–4 h)

**Enables:** session history and retrieval in **AWS** (shared across laptops / AgentCore console).

### Option A — Script (fastest)

```bash
cd helm && source .venv/bin/activate
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
HELM_USE_LOCAL_MEMORY=false
HELM_USE_LOCAL_POLICY=true   # still local until Gateway (Tier 3)
HELM_MOCK_BEDROCK=0
```

Restart uvicorn. MCP `helm_declare_intent` + `helm_get_history` now persist to AgentCore.

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

Uploads statements from `backend/bedrock/policies/helm_coordination.cedar`.

Set in `.env`:

```bash
AGENTCORE_POLICY_ENGINE_ID=<engine id>
HELM_USE_LOCAL_POLICY=false
```

**Important:** Until **Gateway** is attached, Helm still evaluates rules in Python (`agentcore_policy._evaluate_local`) using the same semantics as Cedar. Cloud engine holds the **governed copy** for judges; Gateway adds **ENFORCE at tool call**.

---

## Tier 4 — AgentCore Gateway (optional, ~8–12 h)

Native policy **ENFORCE** runs when agents call tools **through the Gateway**, not direct HTTP.

### Tools to expose

| Gateway tool name | Helm backend |
|-------------------|------------------|
| `Helm___declare_intent` | `POST /intents` |
| `Helm___proposed_write` | `POST /guardrails/check` |
| `Helm___resolve_conflict` | `POST /resolve` |

### CLI flow (AWS docs)

```bash
npm install -g @aws/agentcore
agentcore create --name HelmGateway --defaults
cd HelmGateway
# Add OpenAPI/HTTP target → your deployed Helm URL (or ngrok for demo)
agentcore add gateway --name HelmGW --authorizer-type NONE
agentcore add policy-engine --name HelmPolicy --attach-to-gateways HelmGW --attach-mode ENFORCE
agentcore add policy --name CoordinationRules --engine HelmPolicy \
  --source ../backend/bedrock/policies/helm_coordination.cedar
agentcore deploy
agentcore status   # gateway URL + ARNs
```

After deploy, update Cedar `resource` lines with the **gateway ARN** from `agentcore status` (wildcards are rejected).

Set `AGENTCORE_GATEWAY_ARN` in `.env` for documentation; point MCP/agents at Gateway MCP URL instead of raw FastAPI when ready.

See also: [`infra/agentcore/README.md`](../infra/agentcore/README.md).

---

## Recommended `.env` matrix

| Demo | `HELM_MOCK_BEDROCK` | `USE_LOCAL_MEMORY` | `USE_LOCAL_POLICY` |
|------|-------------------------|--------------------|--------------------|
| Offline / CI | `1` | `true` | `true` |
| Live Sonnet only | `0` | `true` | `true` |
| Full cloud memory | `0` | `false` + `AGENTCORE_MEMORY_ID` | `true` |
| Full AWS story | `0` | `false` | `false` + `AGENTCORE_POLICY_ENGINE_ID` |

---

## End-to-end checklist (judges)

```bash
cd helm && source .venv/bin/activate
cp .env.example .env   # fill IDs after bootstrap

# 1) Infra
python scripts/bootstrap_agentcore.py
python scripts/verify_aws_setup.py

# 2) Server
export HELM_MOCK_BEDROCK=0
cd backend && uvicorn main:app --port 8000

# 3) Mock-off smoke (Acts 1 & 3 hit Bedrock; Act 2 simulator)
curl -s http://127.0.0.1:8000/demo/smoke | python3 -m json.tool

# 4) MCP agent session
# Cursor → helm MCP with HELM_API_BASE=http://127.0.0.1:8000
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `AccessDeniedException` on invoke | Enable model in Bedrock console; check region `us-east-1` |
| `ValidationException` model ID / inference profile | Use `us.anthropic.*` IDs in `.env` (e.g. Sonnet `us.anthropic.claude-sonnet-4-6`, Haiku `us.anthropic.claude-haiku-4-5-20251001-v1:0`). Raw `anthropic.*` IDs are auto-prefixed in code. |
| Memory writes fail | Set `AGENTCORE_MEMORY_ID`, `HELM_USE_LOCAL_MEMORY=false` |
| Policy upload fails Cedar validation | Deploy Gateway first, put gateway ARN in `resource`; or use `validationMode=IGNORE_ALL_FINDINGS` in bootstrap script |
| MCP sees stale data | Same `session_id` across `declare_intent` / `guardrail_check` |
| Guardrail demo empty history | Demo uses session `guardrail-demo`; call `POST /guardrail/check` not raw check without seed |

---

## Clean up

Delete Memory, Policy Engine, and Gateway in console (or `agentcore remove` + `agentcore deploy`) to avoid hackathon charges.
