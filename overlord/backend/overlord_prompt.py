import json

from arbitration.prompt import build_merge_conflict_prompt

__all__ = [
    "build_merge_conflict_prompt",
    "build_intent_conflict_prompt",
    "build_guardrail_resolution_prompt",
]


def build_intent_conflict_prompt(agent_a: dict, agent_b: dict) -> str:
    schema = {
        "conflict_type": "intent_conflict",
        "reasoning": "string — why these intents conflict and how you compromised",
        "resolved_code": "string — unified intent directive BOTH agents should follow (2-4 sentences); may include short code sketch",
        "tokens_saved_estimate": "string — e.g. '~1800 tokens saved vs agents looping on goals'",
    }
    return f"""You are Overlord, resolving INTENT CONFLICTS between two AI coding agents.

The agents have NOT necessarily edited the same lines yet, but their stated goals contradict.
Your job:
1. Explain the incompatibility between Agent A and Agent B intents.
2. Produce ONE compromise directive both agents can follow before writing more code.
3. Prefer performance where it does not add dependencies; prefer native/stdlib over new packages.
4. Set conflict_type to exactly "intent_conflict".

Agent A intent: {agent_a["intent"]}

Agent A planned code:
{agent_a["code"]}

Agent B intent: {agent_b["intent"]}

Agent B planned code:
{agent_b["code"]}

Respond ONLY with a single JSON object matching this schema (no markdown, no preamble):
{json.dumps(schema, indent=2)}
"""


def build_guardrail_resolution_prompt(
    agent_a: dict,
    agent_b: dict,
    proposed_action: dict,
    rule: str,
    message: str,
) -> str:
    schema = {
        "conflict_type": "proactive_guardrail",
        "reasoning": "string — why the guardrail tripped and your verdict",
        "resolved_code": "string — what Agent B should do instead (e.g. refactor around cache)",
        "tokens_saved_estimate": "string",
        "verdict": "modify | block | allow_with_changes",
    }
    return f"""You are Overlord. A proactive guardrail BLOCKED an agent action before execution.

Guardrail rule: {rule}
Guardrail message: {message}

Proposed action: {json.dumps(proposed_action, indent=2)}

Agent A intent: {agent_a.get("intent", "")}
Agent A code context: {agent_a.get("code", "")}

Agent B intent: {agent_b.get("intent", "")}
Agent B code context: {agent_b.get("code", "")}

Decide how Agent B should proceed. Set conflict_type to "proactive_guardrail".
Respond ONLY with JSON matching:
{json.dumps(schema, indent=2)}
"""
