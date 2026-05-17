"""Self-contained arbitration logic for AgentCore Runtime zip deploy (no backend/ import)."""

from __future__ import annotations

import json
import os
import re
from typing import Any

import boto3
from pydantic import BaseModel

HELM_MODEL = os.getenv(
    "HELM_BEDROCK_MODEL",
    "us.anthropic.claude-sonnet-4-6",
)
MAX_TOKENS = 1500
_REGION = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION", "us-east-1")

_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


class ArbitrationResult(BaseModel):
    conflict_type: str
    reasoning: str
    resolved_code: str
    tokens_saved_estimate: str


def _agent_payload_valid(agent: Any) -> bool:
    return (
        isinstance(agent, dict)
        and isinstance(agent.get("intent"), str)
        and isinstance(agent.get("code"), str)
    )


def parse_invoke_request(request: dict[str, Any]) -> tuple[dict, dict, Any | None]:
    """Accept FastAPI shape or CLI shape (JSON nested under ``prompt``)."""
    agent_a = request.get("agent_a")
    agent_b = request.get("agent_b")
    if _agent_payload_valid(agent_a) and _agent_payload_valid(agent_b):
        return agent_a, agent_b, request.get("kb_context")

    prompt = request.get("prompt")
    if isinstance(prompt, str):
        try:
            parsed = json.loads(prompt)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "Invalid payload: 'prompt' must be JSON with agent_a and agent_b."
            ) from exc
        if isinstance(parsed, dict):
            agent_a = parsed.get("agent_a")
            agent_b = parsed.get("agent_b")
            if _agent_payload_valid(agent_a) and _agent_payload_valid(agent_b):
                return agent_a, agent_b, parsed.get("kb_context")

    raise ValueError(
        "Invalid payload. Required: "
        '{"agent_a": {"intent": "...", "code": "..."}, '
        '"agent_b": {"intent": "...", "code": "..."}}. '
        "CLI: save JSON to a file and run "
        "`agentcore invoke --runtime HelmArbitrator --prompt-file payload.json` "
        "(--json is output-only, not input)."
    )


def build_merge_conflict_prompt(agent_a: dict, agent_b: dict) -> str:
    schema = {
        "conflict_type": "merge_conflict",
        "reasoning": "string — why you merged this way and what you prioritized",
        "resolved_code": "string — single unified code output",
        "tokens_saved_estimate": "string — e.g. '~2400 tokens saved vs two agents fixing independently'",
    }
    return f"""You are Helm, a supervisor agent resolving MERGE CONFLICTS between two AI coding agents.

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


def extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    fence_match = _FENCE_RE.search(stripped)
    if fence_match:
        stripped = fence_match.group(1).strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in model output")
    return json.loads(stripped[start : end + 1])


def run_arbitration(
    agent_a: dict,
    agent_b: dict,
    kb_context: str | list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    client = boto3.client("bedrock-runtime", region_name=_REGION)
    prompt = build_merge_conflict_prompt(agent_a, agent_b)
    if kb_context:
        kb_text = (
            json.dumps(kb_context, indent=2)
            if isinstance(kb_context, list)
            else kb_context
        )
        prompt += f"\n\nRelevant history from Knowledge Base:\n{kb_text}"

    response = client.invoke_model(
        modelId=HELM_MODEL,
        body=json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": MAX_TOKENS,
                "messages": [{"role": "user", "content": prompt}],
            }
        ),
    )
    payload = json.loads(response["body"].read())
    text = payload["content"][0]["text"]
    raw = extract_json_object(text)
    return ArbitrationResult.model_validate(raw).model_dump()
