# AgentCore setup (Memory + Policy)

**Full hackathon guide:** [`docs/AWS_SETUP.md`](../../docs/AWS_SETUP.md)  
**Automation:** `python scripts/bootstrap_agentcore.py` · `python scripts/verify_aws_setup.py`

## Memory

1. In AWS Console → **Amazon Bedrock AgentCore** → **Memory**, create a memory resource.
2. Note `AGENTCORE_MEMORY_ID` and set in `helm/.env`.
3. Namespace pattern used by Helm: `helm/sessions/{sessionId}/agents/{actorId}/`

Local dev: leave `HELM_USE_LOCAL_MEMORY=true` (default) — uses `HELM_SESSION_PATH` JSON file.

## Policy Engine

1. Create a **Policy Engine** in AgentCore.
2. Upload statements from `helm/backend/bedrock/policies/helm_coordination.cedar`.
3. Set `AGENTCORE_POLICY_ENGINE_ID` in `.env`.

Local dev: `HELM_USE_LOCAL_POLICY=true` applies the same rules in Python (`agentcore_policy.py`).

## Gateway (optional — native Policy at tool call)

Expose Helm HTTP tools on an AgentCore Gateway and attach the Policy Engine:

| Gateway tool | Backend |
|--------------|---------|
| `Helm___declare_intent` | `POST /intents` |
| `Helm___proposed_write` | `POST /guardrails/check` |
| `Helm___resolve_conflict` | `POST /resolve` |

Until Gateway is wired, `/guardrails/check` uses the policy **bridge** (Memory context + local Cedar semantics).
