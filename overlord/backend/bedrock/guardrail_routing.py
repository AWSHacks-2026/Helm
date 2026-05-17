"""Select Haiku vs Sonnet for guardrail arbitration based on incident complexity."""

from __future__ import annotations

import os
from typing import Any

from bedrock.inference_routing import (
    ComplexityInput,
    max_tokens_for_tier,
    model_id_for_tier,
    select_inference_tier,
    sonnet_min_agents as inference_sonnet_min_agents,
)


def guardrail_strategy() -> str:
    return os.getenv("GUARDRAIL_STRATEGY", "tiered").strip().lower()


def sonnet_min_agents() -> int:
    return inference_sonnet_min_agents()


def sonnet_min_files() -> int:
    return int(os.getenv("GUARDRAIL_SONNET_MIN_FILES", "2"))


def sonnet_kb_event_threshold() -> int:
    return int(os.getenv("GUARDRAIL_SONNET_KB_EVENTS", "8"))


def sonnet_rules() -> set[str]:
    raw = os.getenv("GUARDRAIL_SONNET_RULES", "intent_contradiction")
    return {r.strip() for r in raw.split(",") if r.strip()}


def escalate_sonnet_enabled() -> bool:
    return os.getenv("GUARDRAIL_ESCALATE_SONNET", "0") == "1"


def count_distinct_files(
    proposed_action: dict[str, Any] | None,
    kb_context: list[dict[str, Any]] | None,
) -> int:
    paths: set[str] = set()
    if proposed_action:
        path = proposed_action.get("file_path")
        if path:
            paths.add(str(path))
    for event in kb_context or []:
        if not isinstance(event, dict):
            continue
        path = event.get("file_path") or event.get("path")
        if path:
            paths.add(str(path))
    return len(paths)


def select_guardrail_tier(
    *,
    agent_count: int,
    preflight_rule: str | None = None,
    kb_context: list[dict[str, Any]] | None = None,
    proposed_action: dict[str, Any] | None = None,
) -> str:
    """Return ``haiku`` or ``sonnet`` for the guardrail LLM call."""
    strategy = guardrail_strategy()
    if strategy == "haiku":
        return "haiku"
    if strategy == "sonnet":
        return "sonnet"

    if agent_count >= sonnet_min_agents():
        return "sonnet"

    if preflight_rule and preflight_rule in sonnet_rules():
        return "sonnet"

    if count_distinct_files(proposed_action, kb_context) >= sonnet_min_files():
        return "sonnet"

    if kb_context and len(kb_context) >= sonnet_kb_event_threshold():
        return "sonnet"

    file_count = count_distinct_files(proposed_action, kb_context)
    inp = ComplexityInput(
        operation="guardrail",
        agent_count=agent_count,
        file_count=file_count,
        kb_event_count=len(kb_context or []),
        total_text_chars=len(str(proposed_action or {})),
        preflight_rule=preflight_rule,
        has_substantive_code=False,
    )
    return select_inference_tier(inp)


__all__ = [
    "count_distinct_files",
    "escalate_sonnet_enabled",
    "guardrail_strategy",
    "max_tokens_for_tier",
    "model_id_for_tier",
    "select_guardrail_tier",
    "sonnet_min_agents",
]
