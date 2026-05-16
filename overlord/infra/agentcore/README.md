# AgentCore setup (Memory + Policy)

**Full hackathon guide:** [`docs/AWS_SETUP.md`](../../docs/AWS_SETUP.md)  
**Automation:** `python scripts/bootstrap_agentcore.py` · `python scripts/verify_aws_setup.py`

## Memory

1. In AWS Console → **Amazon Bedrock AgentCore** → **Memory**, create a memory resource.
2. Note `AGENTCORE_MEMORY_ID` and set in `overlord/.env`.
3. Namespace pattern used by Overlord: `overlord/sessions/{sessionId}/agents/{actorId}/`

Local dev: leave `OVERLORD_USE_LOCAL_MEMORY=true` (default) — uses `OVERLORD_SESSION_PATH` JSON file.

## Policy Engine

1. Create a **Policy Engine** in AgentCore.
2. Upload statements from `overlord/backend/bedrock/policies/overlord_coordination.cedar`.
3. Set `AGENTCORE_POLICY_ENGINE_ID` in `.env`.

Local dev: `OVERLORD_USE_LOCAL_POLICY=true` applies the same rules in Python (`agentcore_policy.py`).

## Gateway (optional — native Policy at tool call)

Expose Overlord HTTP tools on an AgentCore Gateway and attach the Policy Engine:

| Gateway tool | Backend |
|--------------|---------|
| `Overlord___declare_intent` | `POST /intents` |
| `Overlord___proposed_write` | `POST /guardrails/check` |
| `Overlord___resolve_conflict` | `POST /resolve` |

Until Gateway is wired, `/guardrails/check` uses the policy **bridge** (Memory context + local Cedar semantics).
