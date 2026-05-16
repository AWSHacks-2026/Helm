from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from bedrock import knowledge_base as kb

_DELETE_ACTIONS = {"delete_file", "remove_file", "delete"}
_ADD_ACTIONS = {"add_file", "create_file", "add"}
_CONTRADICTION_PAIRS = [
    (("cache", "caching"), ("remove", "delete", "strip", "minimize")),
    (("performance", "speed", "optimize"), ("minimal", "dependency", "simplify")),
]


@dataclass
class PreflightResult:
    allowed: bool
    rule: str | None = None
    message: str = ""
    kb_context: list[dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "rule": self.rule,
            "message": self.message,
            "kb_context": self.kb_context or [],
        }


def _check_reverses_recent_decision(proposed: dict[str, Any]) -> PreflightResult | None:
    action_type = proposed.get("action_type", "")
    file_path = proposed.get("file_path", "")
    if action_type not in _DELETE_ACTIONS or not file_path:
        return None

    recent = kb.get_history(limit=20, record_type="action")
    adds_by_other = [
        r
        for r in recent
        if r["agent_id"] != proposed["agent_id"]
        and r["payload"].get("file_path") == file_path
        and r["payload"].get("action_type") in _ADD_ACTIONS
    ]
    if not adds_by_other:
        return None

    last_add = adds_by_other[-1]
    ctx = kb.retrieve_context(
        f"{file_path} cache utility {last_add['agent_id']}", max_results=5
    )
    return PreflightResult(
        allowed=False,
        rule="reverses_recent_decision",
        message=(
            f"Blocked: {proposed['agent_id']} would delete {file_path}, but "
            f"{last_add['agent_id']} added or extended it recently "
            f"({last_add['payload'].get('description', '')})."
        ),
        kb_context=ctx,
    )


def _check_intent_contradiction(proposed: dict[str, Any]) -> PreflightResult | None:
    intents = kb.get_history(limit=20, record_type="intent")
    description = (proposed.get("description") or "").lower()
    for record in intents:
        if record["agent_id"] == proposed["agent_id"]:
            continue
        intent_text = record["payload"].get("intent", "").lower()
        for positive, negative in _CONTRADICTION_PAIRS:
            if any(p in intent_text for p in positive) and any(
                n in description for n in negative
            ):
                ctx = kb.retrieve_context(intent_text + " " + description, max_results=5)
                return PreflightResult(
                    allowed=False,
                    rule="intent_contradiction",
                    message=(
                        f"Intent conflict: {record['agent_id']} ({intent_text}) vs "
                        f"{proposed['agent_id']} action ({description})."
                    ),
                    kb_context=ctx,
                )
    return None


def _check_file_overlap(proposed_action: dict[str, Any]) -> PreflightResult | None:
    agent_id = proposed_action["agent_id"]
    file_path = proposed_action.get("file_path", "")
    history = kb.get_history(limit=100, record_type="action")

    for record in history:
        if record["agent_id"] == agent_id:
            continue
        other_path = record["payload"].get("file_path", "")
        if file_path and other_path == file_path:
            ctx = kb.retrieve_context(
                f"{file_path} {record['agent_id']} {record['payload'].get('description', '')}",
                max_results=5,
            )
            return PreflightResult(
                allowed=False,
                rule="file_overlap",
                message=(
                    f"{record['agent_id']} already touched {file_path}; "
                    f"{agent_id} must coordinate before modifying."
                ),
                kb_context=ctx,
            )
    return None


def preflight_check(proposed_action: dict[str, Any]) -> PreflightResult:
    reversed_result = _check_reverses_recent_decision(proposed_action)
    if reversed_result:
        return reversed_result

    intent_result = _check_intent_contradiction(proposed_action)
    if intent_result:
        return intent_result

    overlap_result = _check_file_overlap(proposed_action)
    if overlap_result:
        return overlap_result

    bedrock_result = apply_bedrock_guardrail(
        proposed_action.get("description", "") or str(proposed_action)
    )
    if bedrock_result and bedrock_result.get("action") == "GUARDRAIL_INTERVENED":
        return PreflightResult(
            allowed=False,
            rule="bedrock_guardrail",
            message="Bedrock Guardrail intervened on proposed action text.",
        )

    return PreflightResult(allowed=True, message="No conflicts detected.")


def apply_bedrock_guardrail(text: str) -> dict[str, Any] | None:
    guardrail_id = os.getenv("BEDROCK_GUARDRAIL_ID", "").strip()
    if not guardrail_id:
        return None

    from bedrock.client import get_bedrock_runtime_client

    client = get_bedrock_runtime_client()
    version = os.getenv("BEDROCK_GUARDRAIL_VERSION", "DRAFT")
    return client.apply_guardrail(
        guardrailIdentifier=guardrail_id,
        guardrailVersion=version,
        source="INPUT",
        content=[{"text": {"text": text}}],
    )


def _arbitrate(
    agent_a: dict[str, str],
    agent_b: dict[str, str],
    kb_context: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    from overlord import arbitrate

    return arbitrate(agent_a, agent_b, kb_context=kb_context)


def handle_proposed_action(
    proposed_action: dict[str, Any],
    agent_a: dict[str, str],
    agent_b: dict[str, str],
) -> dict[str, Any]:
    preflight = preflight_check(proposed_action)
    if preflight.allowed:
        kb.log_action(
            agent_id=proposed_action["agent_id"],
            action_type=proposed_action.get("action_type", "unknown"),
            file_path=proposed_action.get("file_path", ""),
            description=proposed_action.get("description", ""),
        )
        return {"preflight": preflight.to_dict(), "resolution": None, "executed": True}

    resolution = _arbitrate(agent_a, agent_b, kb_context=preflight.kb_context)
    kb.log_decision(
        reasoning=resolution.get("reasoning", ""),
        affected_agents=["agent_a", "agent_b"],
    )
    return {
        "preflight": preflight.to_dict(),
        "resolution": resolution,
        "executed": False,
        "verdict": resolution.get("verdict", "blocked"),
    }


GUARDRAIL_DEMO_SCENARIO = {
    "agent_a": {
        "intent": "Add caching utilities to improve get_user() response times",
        "code": "# utils/cache.py — CacheManager with TTL support",
    },
    "agent_b": {
        "intent": "Remove unused utilities to reduce maintenance burden",
        "code": "# planned: delete utils/cache.py",
    },
    "proposed_action": {
        "agent_id": "agent_b",
        "action_type": "delete_file",
        "file_path": "utils/cache.py",
        "description": "Remove caching utility — appears unused",
    },
}


def seed_guardrail_demo() -> None:
    kb.log_intent("agent_a", GUARDRAIL_DEMO_SCENARIO["agent_a"]["intent"])
    kb.log_action("agent_a", "add_file", "utils/cache.py", "Added caching utility")
    kb.log_action("agent_a", "modify_file", "utils/cache.py", "Extended cache API")
    kb.log_action("agent_a", "add_file", "utils/cache.py", "Documented cache usage")
    kb.log_intent("agent_b", GUARDRAIL_DEMO_SCENARIO["agent_b"]["intent"])
