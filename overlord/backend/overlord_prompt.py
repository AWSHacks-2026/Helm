import json

from arbitration.prompt import build_merge_conflict_prompt

__all__ = [
    "build_merge_conflict_prompt",
    "build_intent_conflict_prompt",
    "build_guardrail_resolution_prompt",
    "build_multi_agent_guardrail_prompt",
    "build_task_deduplication_prompt",
    "build_multi_agent_deduplication_prompt",
    "build_multi_agent_merge_prompt",
    "build_single_file_merge_prompt",
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


def build_multi_agent_guardrail_prompt(
    agents: dict[str, dict],
    proposed_action: dict,
    rule: str,
    message: str,
) -> str:
    blocks: list[str] = []
    for agent_id, agent in agents.items():
        blocks.append(
            f"### {agent_id}\n"
            f"Intent: {agent.get('intent', '')}\n"
            f"Code context: {agent.get('code', '')}\n"
        )
    agent_list = ", ".join(f'"{aid}"' for aid in agents)
    schema = {
        "conflict_type": "proactive_guardrail",
        "reasoning": "string — why the guardrail tripped and coordinated verdict",
        "resolved_code": "string — what the proposing agent should do instead",
        "tokens_saved_estimate": "string",
        "verdict": "modify | block | allow_with_changes",
        "agent_directives": {
            "agent_b": "concrete next step for the agent who proposed the blocked action"
        },
    }
    return f"""You are Overlord. A proactive guardrail BLOCKED an agent action in a multi-agent fleet.

Guardrail rule: {rule}
Guardrail message: {message}

Proposed action: {json.dumps(proposed_action, indent=2)}

Fleet context:
{"".join(blocks)}

Coordinate a safe path for ALL agents. The proposing agent must not undo recent peer work.
Set conflict_type to "proactive_guardrail".
Respond ONLY with JSON matching:
{json.dumps(schema, indent=2)}

Rules:
- agent_directives keys must be drawn from: {agent_list}
- Include at least the proposing agent ({proposed_action.get("agent_id", "agent_b")}) in agent_directives.
""".strip()


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


def build_multi_agent_deduplication_prompt(agents: dict[str, dict]) -> str:
    blocks: list[str] = []
    for agent_id, agent in agents.items():
        blocks.append(
            f"### {agent_id}\n"
            f"Intent: {agent['intent']}\n"
            f"Proposed action: {agent.get('proposed_action', '')}\n"
            f"Code or plan: {agent.get('code', '')}\n"
        )
    agent_list = ", ".join(f'"{aid}"' for aid in agents)
    return f"""
You are Overlord, a supervisor for multiple AI coding agents on one codebase.

Perform semantic task deduplication across ALL agents below before they waste work.

{"".join(blocks)}

Your job:
1. Identify groups of semantically overlapping tasks (e.g. multiple agents all building auth).
2. For each overlap group, pick exactly ONE agent to continue the primary implementation.
3. Reassign every other agent in that group to a concrete, non-overlapping follow-up task.
4. Agents with unique non-overlapping work should be listed under continuations.
5. Explain reasoning in one concise paragraph.

Respond ONLY in JSON with this exact shape:
{{
  "conflict_type": "duplicate_work",
  "duplicate_detected": true,
  "continuations": ["agent_a"],
  "reassignments": [
    {{"agent_id": "agent_b", "suggested_new_task": "Implement audit logging for auth events."}},
    {{"agent_id": "agent_c", "suggested_new_task": "Add rate limiting middleware for login routes."}}
  ],
  "reasoning": "Multiple agents were duplicating authentication; one continues, others split to adjacent work."
}}

Rules:
- continuations and reassignments agent_id values must be from: {agent_list}
- Every agent must appear exactly once (either in continuations or reassignments).
- suggested_new_task must not overlap the continuing agent's work in the same group.
""".strip()


def build_multi_agent_merge_prompt(
    agents: dict[str, dict],
    file_paths: dict[str, str],
) -> str:
    blocks: list[str] = []
    for agent_id, agent in agents.items():
        path = file_paths.get(agent_id, "")
        blocks.append(
            f"### {agent_id} (`{path}`)\n"
            f"Intent: {agent['intent']}\n"
            f"Code:\n```python\n{agent.get('code', '')}\n```\n"
        )
    paths = sorted(set(file_paths.values()))
    path_list = ", ".join(f'"{p}"' for p in paths)
    return f"""
You are Overlord, resolving MERGE CONFLICTS across multiple AI coding agents.

Each agent edited the same commerce codebase with incompatible implementations.
Produce ONE merged Python module per affected file that honors both intents where possible.

{"".join(blocks)}

Your job:
1. Group agents by file path and merge their conflicting code into a single coherent module per file.
2. Preserve complementary features (e.g. caching AND type hints) when intents allow.
3. Do NOT leave git conflict markers.
4. Explain reasoning in one concise paragraph.

Respond ONLY in JSON with this exact shape:
{{
  "conflict_type": "merge_conflict",
  "resolutions": [
    {{"file_path": "app/auth/handlers.py", "resolved_code": "# full merged python for this file"}},
    {{"file_path": "app/catalog/products.py", "resolved_code": "# full merged python"}}
  ],
  "reasoning": "How you unified each file.",
  "tokens_saved_estimate": "~5000 tokens saved vs six agents merge-fix thrashing"
}}

Rules:
- resolutions must include exactly these file paths: {path_list}
- resolved_code must be complete valid Python for that file (no markdown fences).
""".strip()


def build_single_file_merge_prompt(file_path: str, agents: dict[str, dict]) -> str:
    blocks: list[str] = []
    for agent_id, agent in agents.items():
        blocks.append(
            f"### {agent_id}\n"
            f"Intent: {agent['intent']}\n"
            f"Code:\n```python\n{agent.get('code', '')}\n```\n"
        )
    return f"""
You are Overlord, resolving a MERGE CONFLICT on `{file_path}`.

Multiple agents produced incompatible implementations for this file.
Produce ONE merged Python module that honors complementary intents where possible.
Do NOT leave git conflict markers.

{"".join(blocks)}

Respond ONLY in JSON with this exact shape:
{{
  "conflict_type": "merge_conflict",
  "resolved_code": "# complete valid Python for {file_path}",
  "reasoning": "Brief explanation of how you merged the agents.",
  "tokens_saved_estimate": "~1500"
}}

Rules:
- resolved_code must be complete valid Python (no markdown fences).
""".strip()
