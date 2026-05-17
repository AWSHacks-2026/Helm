from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from bedrock import agentcore_memory as mem

_DELETE_ACTIONS = {"delete_file", "remove_file", "delete"}
_ADD_ACTIONS = {"add_file", "create_file", "add"}
_CONTRADICTION_PAIRS = [
    (("cache", "caching"), ("remove", "delete", "strip", "minimize")),
    (("performance", "speed", "optimize"), ("minimal", "dependency", "simplify")),
]


@dataclass
class PolicyResult:
    allowed: bool
    rule: str | None = None
    message: str = ""
    kb_context: list[dict[str, Any]] | None = None


def _use_local() -> bool:
    return os.getenv("HELM_USE_LOCAL_POLICY", "true").lower() == "true"


def build_policy_context(session_id: str, proposed_action: dict[str, Any]) -> dict[str, Any]:
    events = mem.list_events(session_id, limit=100)
    agent_id = proposed_action["agent_id"]
    file_path = proposed_action.get("file_path", "")
    action_type = proposed_action.get("action_type", "")
    description = (proposed_action.get("description") or "").lower()

    peer_recently_added = False
    file_overlap = False
    intent_contradiction = False
    peer_agent_id: str | None = None
    overlap_agent_id: str | None = None
    intent_peer_id: str | None = None

    for ev in events:
        p = ev.get("payload", {})
        other = ev.get("actor_id")
        if other == agent_id:
            continue
        if (
            action_type in _DELETE_ACTIONS
            and p.get("file_path") == file_path
            and p.get("action_type") in _ADD_ACTIONS
        ):
            peer_recently_added = True
            peer_agent_id = other
        if file_path and p.get("file_path") == file_path and ev.get("record_type") == "action":
            file_overlap = True
            overlap_agent_id = other
        if ev.get("record_type") == "intent":
            intent_text = (p.get("intent") or "").lower()
            for positive, negative in _CONTRADICTION_PAIRS:
                if any(tok in intent_text for tok in positive) and any(
                    tok in description for tok in negative
                ):
                    intent_contradiction = True
                    intent_peer_id = other

    return {
        "agent_id": agent_id,
        "action_type": action_type,
        "file_path": file_path,
        "description": proposed_action.get("description", ""),
        "peer_recently_added_same_file": peer_recently_added,
        "file_overlap": file_overlap,
        "intent_contradiction": intent_contradiction,
        "peer_agent_id": peer_agent_id,
        "overlap_agent_id": overlap_agent_id,
        "intent_peer_id": intent_peer_id,
    }


def evaluate_proposed_action(session_id: str, proposed_action: dict[str, Any]) -> PolicyResult:
    ctx = build_policy_context(session_id, proposed_action)
    kb_context = mem.retrieve_context(
        session_id,
        f"{proposed_action.get('file_path', '')} {proposed_action.get('description', '')}",
        top_k=5,
    )

    if _use_local() or not os.getenv("AGENTCORE_POLICY_ENGINE_ID", "").strip():
        return _evaluate_local(ctx, kb_context)

    return _evaluate_via_agentcore(ctx, kb_context)


def _evaluate_local(ctx: dict[str, Any], kb_context: list[dict[str, Any]]) -> PolicyResult:
    if ctx.get("peer_recently_added_same_file"):
        peer = ctx.get("peer_agent_id") or "peer agent"
        return PolicyResult(
            allowed=False,
            rule="reverses_recent_decision",
            message=(
                f"Blocked: {ctx['agent_id']} would delete {ctx['file_path']}, but "
                f"{peer} added or extended it recently."
            ),
            kb_context=kb_context,
        )
    if ctx.get("file_overlap"):
        other = ctx.get("overlap_agent_id") or "another agent"
        return PolicyResult(
            allowed=False,
            rule="file_overlap",
            message=(
                f"{other} already touched {ctx['file_path']}; "
                f"{ctx['agent_id']} must coordinate before modifying."
            ),
            kb_context=kb_context,
        )
    if ctx.get("intent_contradiction"):
        peer = ctx.get("intent_peer_id") or "peer agent"
        return PolicyResult(
            allowed=False,
            rule="intent_contradiction",
            message=(
                f"Intent conflict: {peer} vs {ctx['agent_id']} action ({ctx['description']})."
            ),
            kb_context=kb_context,
        )
    return PolicyResult(allowed=True, message="Policy permit.", kb_context=kb_context)


def _evaluate_via_agentcore(
    ctx: dict[str, Any],
    kb_context: list[dict[str, Any]],
) -> PolicyResult:
    # Gateway-native evaluation lands in Task 6; semantics match local Cedar rules.
    return _evaluate_local(ctx, kb_context)
