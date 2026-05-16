from __future__ import annotations

import os
import time
from typing import Any

from fastapi import APIRouter, HTTPException

from agents.merge_evaluator import evaluate_merge_resolution
from agents.merge_scenarios import (
    MERGE_MOCK_RESOLUTIONS,
    get_merge_meta,
    get_merge_scenario,
    get_merge_scenario_names,
)
from agents.naive_merge import NAIVE_STRATEGIES
from overlord import arbitrate

router = APIRouter(prefix="/merge", tags=["merge-lab"])


def _resolve_overlord(scenario_name: str, scenario: dict[str, Any]) -> dict[str, Any]:
    if os.getenv("OVERLORD_MOCK_BEDROCK") == "1":
        mock = MERGE_MOCK_RESOLUTIONS.get(scenario_name)
        if mock:
            return dict(mock)

    from bedrock import knowledge_base

    kb_context = None
    try:
        kb_context = knowledge_base.get_context_for_agents(
            ["agent_a", "agent_b"],
            module_hint=scenario.get("file_path", ""),
        )
    except Exception:
        kb_context = None

    return arbitrate(
        scenario["agent_a"],
        scenario["agent_b"],
        kb_context=kb_context or None,
        conflict_kind="merge",
    )


def _run_strategy(
    strategy: str,
    scenario_name: str,
    scenario: dict[str, Any],
    acceptance: dict[str, Any],
) -> dict[str, Any]:
    agent_a = scenario["agent_a"]
    agent_b = scenario["agent_b"]

    if strategy == "overlord":
        started = time.perf_counter()
        raw = _resolve_overlord(scenario_name, scenario)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        resolved_code = raw.get("resolved_code", "")
        reasoning = raw.get("reasoning", "")
        extra = {
            "conflict_type": raw.get("conflict_type"),
            "tokens_saved_estimate": raw.get("tokens_saved_estimate"),
        }
    else:
        fn = NAIVE_STRATEGIES.get(strategy)
        if not fn:
            raise ValueError(f"Unknown strategy: {strategy}")
        started = time.perf_counter()
        naive = fn(agent_a, agent_b)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        resolved_code = naive["resolved_code"]
        reasoning = naive["reasoning"]
        extra = {"strategy": naive["strategy"]}

    evaluation = evaluate_merge_resolution(
        resolved_code,
        agent_a["code"],
        agent_b["code"],
        acceptance,
    )
    return {
        "strategy": strategy,
        "resolved_code": resolved_code,
        "reasoning": reasoning,
        "elapsed_ms": elapsed_ms,
        "evaluation": evaluation,
        **extra,
    }


@router.get("/scenarios")
def list_merge_scenarios() -> list[dict[str, str]]:
    return get_merge_meta()


@router.get("/scenarios/{scenario_name}")
def get_merge_scenario_detail(scenario_name: str) -> dict[str, Any]:
    if scenario_name not in get_merge_scenario_names():
        raise HTTPException(status_code=404, detail="Merge scenario not found")
    scenario = get_merge_scenario(scenario_name)
    return {
        "name": scenario_name,
        "meta": next(m for m in get_merge_meta() if m["name"] == scenario_name),
        "file_path": scenario["file_path"],
        "agent_a": scenario["agent_a"],
        "agent_b": scenario["agent_b"],
    }


@router.post("/compare/{scenario_name}")
def compare_merge_strategies(scenario_name: str) -> dict[str, Any]:
    """Run Overlord vs naive baselines; return pass/score for each strategy."""
    if scenario_name not in get_merge_scenario_names():
        raise HTTPException(status_code=404, detail="Merge scenario not found")

    scenario = get_merge_scenario(scenario_name)
    acceptance = scenario.get("acceptance", {})

    strategies = ["overlord", "pick_agent_a", "pick_agent_b", "dual_edit_markers"]
    results = [_run_strategy(s, scenario_name, scenario, acceptance) for s in strategies]

    overlord = next(r for r in results if r["strategy"] == "overlord")
    best_naive = max(
        (r for r in results if r["strategy"] != "overlord"),
        key=lambda r: r["evaluation"]["score"],
    )

    return {
        "scenario": scenario_name,
        "file_path": scenario["file_path"],
        "mock_bedrock": os.getenv("OVERLORD_MOCK_BEDROCK") == "1",
        "agent_a": scenario["agent_a"],
        "agent_b": scenario["agent_b"],
        "results": results,
        "summary": {
            "overlord_passed": overlord["evaluation"]["passed"],
            "overlord_score": overlord["evaluation"]["score"],
            "best_naive_strategy": best_naive["strategy"],
            "best_naive_score": best_naive["evaluation"]["score"],
            "overlord_beats_naive": overlord["evaluation"]["score"] > best_naive["evaluation"]["score"],
            "score_delta": overlord["evaluation"]["score"] - best_naive["evaluation"]["score"],
        },
        "mcp_hint": {
            "tool": "overlord_resolve_conflict",
            "session_id": f"merge-lab-{scenario_name}",
            "file_path": scenario["file_path"],
        },
    }
