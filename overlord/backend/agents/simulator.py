from __future__ import annotations

from typing import Any


WITH_OVERLORD_TOKENS = 800
WITHOUT_OVERLORD_TOKENS = 3200

UNIFIED_INTENT = (
    "Optimize for performance where measurable, but prefer native Python "
    "implementations unless a dependency saves at least 20% latency on the "
    "demo path."
)
PRIORITY_ORDER = [
    "preserve deployability and low dependency count",
    "improve latency with standard-library techniques first",
    "allow a new dependency only with benchmark evidence",
]
AGENT_UPDATES = {
    "agent_a": "Benchmark stdlib json plus functools.lru_cache before proposing orjson.",
    "agent_b": (
        "Keep dependency removals unless Agent A provides benchmark evidence for "
        "a targeted exception."
    ),
}


def _format_history(history: list[dict[str, str]]) -> list[str]:
    return [f"{entry['agent']}: {entry['decision']}" for entry in history]


def _agent_text(agent: dict[str, Any]) -> str:
    return " ".join(
        str(agent.get(field, ""))
        for field in ("intent", "proposed_action", "code")
    ).lower()


def _has_performance_minimalism_conflict(
    agent_a: dict[str, Any],
    agent_b: dict[str, Any],
) -> bool:
    combined = f"{_agent_text(agent_a)} {_agent_text(agent_b)}"
    performance_terms = ("maximum performance", "throughput", "latency", "cache")
    minimalism_terms = (
        "minimize external dependencies",
        "deployment artifact",
        "standard library",
        "low dependency",
    )

    return any(term in combined for term in performance_terms) and any(
        term in combined for term in minimalism_terms
    )


def _token_savings() -> str:
    saved = WITHOUT_OVERLORD_TOKENS - WITH_OVERLORD_TOKENS
    percent = round(saved / WITHOUT_OVERLORD_TOKENS * 100)
    return f"{saved} tokens saved ({percent}%)"


def _resolved_code(unified_intent: str, agent_updates: dict[str, str]) -> str:
    return (
        "Unified directive:\n"
        f"{unified_intent}\n\n"
        f"Agent A update: {agent_updates['agent_a']}\n"
        f"Agent B update: {agent_updates['agent_b']}"
    )


def resolve_intent_conflict(
    agent_a: dict[str, Any],
    agent_b: dict[str, Any],
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    history = history or []

    if not _has_performance_minimalism_conflict(agent_a, agent_b):
        unified_intent = (
            "Proceed with both intents because no direct optimization conflict "
            "was detected."
        )
        agent_updates = {
            "agent_a": "Continue the proposed plan; coordinate with Agent B on shared files.",
            "agent_b": "Continue the proposed plan; coordinate with Agent A on shared files.",
        }

        return {
            "conflict_type": "intent_conflict",
            "compatibility": "compatible",
            "reasoning": (
                "The declared goals can be pursued together without changing "
                "priority because no performance-versus-minimalism tradeoff was found."
            ),
            "unified_intent": unified_intent,
            "priority_order": [
                "preserve both compatible intents",
                "coordinate edits before changing shared code",
            ],
            "agent_updates": agent_updates,
            "resolved_code": _resolved_code(unified_intent, agent_updates),
            "tokens_saved_estimate": _token_savings(),
            "history_used": _format_history(history),
        }

    priority_order = list(PRIORITY_ORDER)
    agent_updates = dict(AGENT_UPDATES)

    return {
        "conflict_type": "intent_conflict",
        "compatibility": "conflict",
        "reasoning": (
            "Agent A's performance goal and Agent B's dependency-minimization "
            "goal conflict before code is written. The compromise keeps the "
            "minimal dependency baseline, then permits performance exceptions "
            "only when benchmark evidence proves a clear demo-path win."
        ),
        "unified_intent": UNIFIED_INTENT,
        "priority_order": priority_order,
        "agent_updates": agent_updates,
        "resolved_code": _resolved_code(UNIFIED_INTENT, agent_updates),
        "tokens_saved_estimate": _token_savings(),
        "history_used": _format_history(history),
    }
