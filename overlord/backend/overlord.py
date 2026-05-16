from __future__ import annotations

import json
import os
from typing import Any

from bedrock.invoke_tracked import invoke_anthropic_messages
from models import BedrockArbitrationResult
from overlord_parse import extract_json_object
from overlord_prompt import (
    build_guardrail_resolution_prompt,
    build_intent_conflict_prompt,
    build_merge_conflict_prompt,
)

from bedrock.model_ids import resolve_inference_profile_id

OVERLORD_MODEL = resolve_inference_profile_id(
    os.getenv(
        "OVERLORD_BEDROCK_MODEL_ID",
        "us.anthropic.claude-sonnet-4-20250514-v1:0",
    )
)
MAX_TOKENS = 1500


def arbitrate(
    agent_a: dict,
    agent_b: dict,
    kb_context: str | list[dict[str, Any]] | None = None,
    conflict_kind: str = "merge",
    guardrail_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Call Sonnet via Bedrock to resolve a conflict between two agents."""
    if os.getenv("OVERLORD_MOCK_BEDROCK") == "1":
        if conflict_kind == "intent":
            return _mock_intent_resolution()
        if conflict_kind == "guardrail":
            return _mock_guardrail_resolution()
        return _mock_merge_resolution()

    prompt = _build_prompt(agent_a, agent_b, conflict_kind, guardrail_context)
    if kb_context:
        kb_text = (
            json.dumps(kb_context, indent=2)
            if isinstance(kb_context, list)
            else kb_context
        )
        prompt += f"\n\nRelevant history from Knowledge Base:\n{kb_text}"

    text, usage = invoke_anthropic_messages(
        model_id=OVERLORD_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=MAX_TOKENS,
        role="overlord",
    )
    result = _parse_arbitration_response(text)
    result["_usage"] = {
        "model_id": usage.model_id,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "latency_ms": usage.latency_ms,
    }
    return result


def _build_prompt(
    agent_a: dict,
    agent_b: dict,
    conflict_kind: str,
    guardrail_context: dict[str, Any] | None,
) -> str:
    if conflict_kind == "intent":
        return build_intent_conflict_prompt(agent_a, agent_b)
    if conflict_kind == "guardrail":
        ctx = guardrail_context or {}
        return build_guardrail_resolution_prompt(
            agent_a,
            agent_b,
            proposed_action=ctx.get("proposed_action", {}),
            rule=ctx.get("rule", ""),
            message=ctx.get("message", ""),
        )
    return build_merge_conflict_prompt(agent_a, agent_b)


def _parse_arbitration_response(text: str) -> dict[str, Any]:
    raw = extract_json_object(text)
    validated = BedrockArbitrationResult.model_validate(raw)
    result = validated.model_dump()
    if "verdict" in raw:
        result["verdict"] = raw["verdict"]
    return result


def _mock_merge_resolution() -> dict[str, Any]:
    return {
        "conflict_type": "merge_conflict",
        "reasoning": "MOCK: Combined Agent A caching with Agent B type hints.",
        "resolved_code": (
            "def get_user(user_id: str) -> User:\n"
            "    if user_id in cache:\n"
            "        return cache[user_id]\n"
            "    result = db.query(user_id)\n"
            "    cache[user_id] = result\n"
            "    return result\n"
        ),
        "tokens_saved_estimate": "~2400 (mock)",
    }


def _mock_intent_resolution() -> dict[str, Any]:
    return {
        "conflict_type": "intent_conflict",
        "reasoning": (
            "MOCK: Agent A optimizes for performance (cache + pooling) while Agent B "
            "minimizes dependencies. Compromise: use stdlib sqlite with a small "
            "in-process LRU cache — no third-party pool."
        ),
        "resolved_code": (
            "Unified directive: Prefer native sqlite3 access with an optional "
            "functools.lru_cache on get_user(); avoid new pip dependencies."
        ),
        "tokens_saved_estimate": "~1800 (mock)",
    }


def _mock_guardrail_resolution() -> dict[str, Any]:
    return {
        "conflict_type": "proactive_guardrail",
        "reasoning": "MOCK: Agent B must not delete utils/cache.py; Agent A invested in caching.",
        "resolved_code": (
            "# Refactor around utils/cache.py: slim the public API instead of deleting."
        ),
        "tokens_saved_estimate": "~2400 (mock)",
        "verdict": "modify",
    }
