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


def build_task_deduplication_prompt(agent_a: dict, agent_b: dict) -> str:
    return f"""
You are Overlord, a supervisor for multiple AI coding agents.

Perform semantic task deduplication before either agent wastes work.

Agent A Intent:
{agent_a["intent"]}

Agent A Proposed Action:
{agent_a.get("proposed_action", "")}

Agent A Current Code Or Plan:
{agent_a.get("code", "")}

Agent B Intent:
{agent_b["intent"]}

Agent B Proposed Action:
{agent_b.get("proposed_action", "")}

Agent B Current Code Or Plan:
{agent_b.get("code", "")}

Your job:
1. Decide whether these agents are working on semantically overlapping tasks.
2. If duplicate work is detected, choose exactly one agent to continue.
3. Choose the other agent to reassign.
4. Suggest a concrete new task for the reassigned agent that does not overlap.
5. Explain the reasoning in one concise paragraph.

Respond ONLY in JSON with this exact shape:
{{
  "conflict_type": "duplicate_work",
  "duplicate_detected": true,
  "agent_to_continue": "agent_a",
  "agent_to_reassign": "agent_b",
  "suggested_new_task": "Implement audit logging for authentication events.",
  "reasoning": "Both agents are implementing overlapping authentication work."
}}
""".strip()
