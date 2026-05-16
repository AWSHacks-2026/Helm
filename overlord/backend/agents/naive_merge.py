"""Baseline merge strategies that simulate agents fixing conflicts independently."""

from __future__ import annotations

from typing import Any


def pick_agent_a(agent_a: dict[str, Any], agent_b: dict[str, Any]) -> dict[str, str]:
    return {
        "strategy": "pick_agent_a",
        "resolved_code": agent_a["code"],
        "reasoning": "Naive: Agent A wins; Agent B changes discarded.",
    }


def pick_agent_b(agent_a: dict[str, Any], agent_b: dict[str, Any]) -> dict[str, str]:
    return {
        "strategy": "pick_agent_b",
        "resolved_code": agent_b["code"],
        "reasoning": "Naive: Agent B wins; Agent A changes discarded.",
    }


def conflict_markers(agent_a: dict[str, Any], agent_b: dict[str, Any]) -> dict[str, str]:
    """Simulates both agents 'fixing' by leaving conflict markers in the file."""
    return {
        "strategy": "dual_edit_markers",
        "resolved_code": (
            f"{agent_a['code']}\n"
            "<<<<<<< agent_a\n"
            f"{agent_a['code']}\n"
            "=======\n"
            f"{agent_b['code']}\n"
            ">>>>>>> agent_b\n"
            f"{agent_b['code']}"
        ),
        "reasoning": "Naive: both agents committed; file still has conflict markers.",
    }


NAIVE_STRATEGIES = {
    "pick_agent_a": pick_agent_a,
    "pick_agent_b": pick_agent_b,
    "dual_edit_markers": conflict_markers,
}
