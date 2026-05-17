from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from bedrock import agentcore_memory as mem
from bedrock import knowledge_base as kb
from bedrock.agentcore_policy import evaluate_proposed_action

_DEFAULT_SESSION = "default"

_ACTION_TYPE_MAP = {
    "write": "modify_file",
    "delete": "delete_file",
    "read": "read_file",
}


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


def preflight_check(
    proposed_action: dict[str, Any],
    session_id: str = _DEFAULT_SESSION,
) -> PreflightResult:
    """Coordination policy via AgentCore Policy bridge + Memory context."""
    result = evaluate_proposed_action(session_id, proposed_action)
    return PreflightResult(
        allowed=result.allowed,
        rule=result.rule,
        message=result.message,
        kb_context=result.kb_context,
    )


def _arbitrate(
    agent_a: dict[str, str],
    agent_b: dict[str, str],
    kb_context: list[dict[str, Any]] | None = None,
    guardrail_context: dict[str, Any] | None = None,
    fleet_agents: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    from overlord import arbitrate

    ctx = dict(guardrail_context or {})
    if fleet_agents:
        ctx["fleet_agents"] = fleet_agents

    return arbitrate(
        agent_a,
        agent_b,
        kb_context=kb_context,
        conflict_kind="guardrail",
        guardrail_context=ctx,
    )


def handle_proposed_action(
    proposed_action: dict[str, Any],
    agent_a: dict[str, str],
    agent_b: dict[str, str],
    session_id: str = _DEFAULT_SESSION,
) -> dict[str, Any]:
    preflight = preflight_check(proposed_action, session_id=session_id)
    if preflight.allowed:
        kb.log_action(
            agent_id=proposed_action["agent_id"],
            action_type=proposed_action.get("action_type", "unknown"),
            file_path=proposed_action.get("file_path", ""),
            description=proposed_action.get("description", ""),
            session_id=session_id,
        )
        return {"preflight": preflight.to_dict(), "resolution": None, "executed": True}

    resolution = _arbitrate(
        agent_a,
        agent_b,
        kb_context=preflight.kb_context,
        guardrail_context={
            "proposed_action": proposed_action,
            "rule": preflight.rule or "",
            "message": preflight.message,
        },
    )
    try:
        kb.log_decision(
            reasoning=resolution.get("reasoning", ""),
            affected_agents=[
                agent_a.get("agent_id", "agent_a"),
                agent_b.get("agent_id", "agent_b"),
            ],
            session_id=session_id,
        )
    except Exception:
        pass
    return {
        "preflight": preflight.to_dict(),
        "resolution": resolution,
        "executed": False,
        "verdict": resolution.get("verdict", "blocked"),
        "resolution_tier": resolution.get("resolution_tier"),
        "escalated_to_sonnet": resolution.get("escalated_to_sonnet", False),
    }


def handle_proposed_action_fleet(
    proposed_action: dict[str, Any],
    agents: dict[str, dict[str, Any]],
    session_id: str = _DEFAULT_SESSION,
) -> dict[str, Any]:
    """Multi-agent guardrail flow (Sonnet when agent count >= GUARDRAIL_SONNET_MIN_AGENTS)."""
    if len(agents) < 3:
        raise ValueError("handle_proposed_action_fleet requires at least 3 agents")

    preflight = preflight_check(proposed_action, session_id=session_id)
    if preflight.allowed:
        kb.log_action(
            agent_id=proposed_action["agent_id"],
            action_type=proposed_action.get("action_type", "unknown"),
            file_path=proposed_action.get("file_path", ""),
            description=proposed_action.get("description", ""),
            session_id=session_id,
        )
        return {"preflight": preflight.to_dict(), "resolution": None, "executed": True}

    ordered = sorted(agents.keys())
    agent_a = {**agents[ordered[0]], "agent_id": ordered[0]}
    agent_b = {**agents[ordered[1]], "agent_id": ordered[1]}

    resolution = _arbitrate(
        agent_a,
        agent_b,
        kb_context=preflight.kb_context,
        guardrail_context={
            "proposed_action": proposed_action,
            "rule": preflight.rule or "",
            "message": preflight.message,
        },
        fleet_agents=agents,
    )
    try:
        kb.log_decision(
            reasoning=resolution.get("reasoning", ""),
            affected_agents=list(agents.keys()),
            session_id=session_id,
        )
    except Exception:
        pass
    return {
        "preflight": preflight.to_dict(),
        "resolution": resolution,
        "executed": False,
        "verdict": resolution.get("verdict", "blocked"),
        "resolution_tier": resolution.get("resolution_tier"),
        "escalated_to_sonnet": resolution.get("escalated_to_sonnet", False),
        "agent_count": len(agents),
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


def seed_guardrail_demo(session_id: str = "guardrail-demo") -> None:
    mem.log_intent(session_id, "agent_a", GUARDRAIL_DEMO_SCENARIO["agent_a"]["intent"])
    mem.log_action(session_id, "agent_a", "add_file", "utils/cache.py", "Added caching utility")
    mem.log_action(session_id, "agent_a", "modify_file", "utils/cache.py", "Extended cache API")
    mem.log_action(session_id, "agent_a", "add_file", "utils/cache.py", "Documented cache usage")
    mem.log_intent(session_id, "agent_b", GUARDRAIL_DEMO_SCENARIO["agent_b"]["intent"])


GUARDRAIL_FLEET_SCENARIO: dict[str, Any] = {
    "agents": {
        "agent_a": {
            "intent": "Own auth handlers and JWT caching on app/auth/handlers.py",
            "code": "# agent_a: JWT + token cache",
        },
        "agent_b": {
            "intent": "Own catalog search API on app/catalog/products.py",
            "code": "# agent_b: search + pagination",
        },
        "agent_c": {
            "intent": "Refactor shared utils/cache.py for auth hot paths",
            "code": "# agent_c: extends cache utilities",
        },
        "agent_d": {
            "intent": "Remove legacy utilities to shrink the repo",
            "code": "# agent_d: cleanup pass",
        },
        "agent_e": {
            "intent": "Billing invoice module on app/billing/invoices.py",
            "code": "# agent_e: invoices",
        },
    },
    "proposed_action": {
        "agent_id": "agent_d",
        "action_type": "delete_file",
        "file_path": "utils/cache.py",
        "description": "Delete shared cache module during repo cleanup",
    },
}


def seed_guardrail_fleet_demo(session_id: str = "guardrail-fleet-demo") -> None:
    mem.log_intent(session_id, "agent_a", GUARDRAIL_FLEET_SCENARIO["agents"]["agent_a"]["intent"])
    mem.log_action(session_id, "agent_a", "modify_file", "app/auth/handlers.py", "JWT cache wiring")
    mem.log_intent(session_id, "agent_b", GUARDRAIL_FLEET_SCENARIO["agents"]["agent_b"]["intent"])
    mem.log_action(session_id, "agent_b", "modify_file", "app/catalog/products.py", "Search API")
    mem.log_intent(session_id, "agent_c", GUARDRAIL_FLEET_SCENARIO["agents"]["agent_c"]["intent"])
    mem.log_action(session_id, "agent_c", "add_file", "utils/cache.py", "Shared cache for auth")
    mem.log_action(session_id, "agent_c", "modify_file", "utils/cache.py", "TTL helpers")
    mem.log_intent(session_id, "agent_d", GUARDRAIL_FLEET_SCENARIO["agents"]["agent_d"]["intent"])
    mem.log_intent(session_id, "agent_e", GUARDRAIL_FLEET_SCENARIO["agents"]["agent_e"]["intent"])


def check_action(
    *,
    session_id: str,
    agent_id: str,
    file_path: str,
    action: str,
    proposed_code: str,
    session_store: Any,
) -> Any:
    """Agentic workflow guardrail check: session store + AgentCore policy preflight."""
    from models import GuardrailCheckResponse

    others = mem.agents_on_file(session_id, file_path, exclude=agent_id)
    if not others:
        others = session_store.agents_on_file(session_id, file_path, exclude=agent_id)
    if action in {"write", "delete"} and others:
        return GuardrailCheckResponse(
            allowed=False,
            reason=f"File {file_path} active for agents: {', '.join(others)}",
            route_to_overlord=True,
        )

    proposed = {
        "agent_id": agent_id,
        "action_type": _ACTION_TYPE_MAP.get(action, action),
        "file_path": file_path,
        "description": proposed_code or f"{action} on {file_path}",
    }
    preflight = preflight_check(proposed, session_id=session_id)
    if not preflight.allowed:
        return GuardrailCheckResponse(
            allowed=False,
            reason=preflight.message,
            route_to_overlord=True,
        )

    return GuardrailCheckResponse(allowed=True)
