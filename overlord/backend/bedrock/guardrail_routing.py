"""Select Haiku vs Sonnet for guardrail arbitration based on incident complexity."""

from __future__ import annotations

import os
from typing import Any

from agents.haiku_agent import agent_model_id
from bedrock.model_ids import resolve_inference_profile_id


def guardrail_strategy() -> str:
    return os.getenv("GUARDRAIL_STRATEGY", "tiered").strip().lower()


def sonnet_model_id() -> str:
    return resolve_inference_profile_id(
        os.getenv("OVERLORD_BEDROCK_MODEL_ID")
        or os.getenv("OVERLORD_BEDROCK_MODEL", "us.anthropic.claude-sonnet-4-6")
    )


def haiku_max_tokens() -> int:
    return int(os.getenv("GUARDRAIL_HAIKU_MAX_TOKENS", "1024"))


def sonnet_max_tokens() -> int:
    return int(os.getenv("GUARDRAIL_SONNET_MAX_TOKENS", "1500"))


def sonnet_min_agents() -> int:
    return int(os.getenv("GUARDRAIL_SONNET_MIN_AGENTS", "3"))


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

    return "haiku"


def model_id_for_tier(tier: str) -> str:
    if tier == "haiku":
        return agent_model_id()
    return sonnet_model_id()


def max_tokens_for_tier(tier: str) -> int:
    if tier == "haiku":
        return haiku_max_tokens()
    return sonnet_max_tokens()
