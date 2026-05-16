import json


def build_merge_conflict_prompt(agent_a: dict, agent_b: dict) -> str:
    schema = {
        "conflict_type": "merge_conflict",
        "reasoning": "string — why you merged this way and what you prioritized",
        "resolved_code": "string — single unified code output",
        "tokens_saved_estimate": "string — e.g. '~2400 tokens saved vs two agents fixing independently'",
    }

    return f"""You are Overlord, a supervisor agent resolving MERGE CONFLICTS between two AI coding agents.

Both agents edited the same function or file in incompatible ways. Your job:
1. Compare the structural differences (signatures, control flow, imports, side effects).
2. Produce ONE unified version that satisfies both agents' stated intents where possible.
3. Prefer combining complementary changes (e.g. caching AND type hints) over picking one side.
4. If intents truly conflict, explain the tradeoff and choose the safer default for production code.
5. Set conflict_type to exactly "merge_conflict".

Agent A intent: {agent_a["intent"]}

Agent A code:
{agent_a["code"]}

Agent B intent: {agent_b["intent"]}

Agent B code:
{agent_b["code"]}

Respond ONLY with a single JSON object matching this schema (no markdown, no preamble):
{json.dumps(schema, indent=2)}
"""
