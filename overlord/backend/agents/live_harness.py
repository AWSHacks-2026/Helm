from __future__ import annotations

import os
import uuid
from typing import Any

from agents.haiku_agent import run_agent_edit, run_agent_merge_fix
from agents.merge_evaluator import evaluate_merge_resolution
from agents.merge_scenarios import get_merge_scenario
from agents.usage_ledger import UsageLedger
from bedrock.cost_estimate import build_cost_comparison
from bedrock import agentcore_memory as mem
from bedrock.invoke_tracked import InvokeUsage
from overlord import arbitrate

MAX_ROUNDS = int(os.getenv("LIVE_BASELINE_MAX_ROUNDS", "3"))


def _live_disabled() -> bool:
    return os.getenv("LIVE_BENCHMARK_DISABLED", "0") == "1"


def _build_artifact(
    scenario: dict[str, Any],
    seed_mode: str,
    ledger: UsageLedger,
) -> dict[str, Any]:
    file_path = scenario["file_path"]
    agent_a = dict(scenario["agent_a"])
    agent_b = dict(scenario["agent_b"])

    if seed_mode == "scenario":
        return {
            "file_path": file_path,
            "agent_a": agent_a,
            "agent_b": agent_b,
        }

    code_a, u1 = run_agent_edit(
        agent_id="agent_a",
        file_path=file_path,
        intent=agent_a["intent"],
        peer_code=None,
    )
    ledger.add(u1)
    code_b, u2 = run_agent_edit(
        agent_id="agent_b",
        file_path=file_path,
        intent=agent_b["intent"],
        peer_code=code_a,
    )
    ledger.add(u2)
    agent_a["code"] = code_a
    agent_b["code"] = code_b
    return {"file_path": file_path, "agent_a": agent_a, "agent_b": agent_b}


def run_baseline_path(
    artifact: dict[str, Any],
    acceptance: dict[str, Any],
    ledger: UsageLedger,
) -> dict[str, Any]:
    file_path = artifact["file_path"]
    code_a = artifact["agent_a"]["code"]
    code_b = artifact["agent_b"]["code"]
    intent_a = artifact["agent_a"]["intent"]
    intent_b = artifact["agent_b"]["intent"]
    rounds = 0

    for _ in range(MAX_ROUNDS):
        rounds += 1
        code_a, u1 = run_agent_merge_fix(
            agent_id="agent_a",
            file_path=file_path,
            intent=intent_a,
            own_code=code_a,
            peer_code=code_b,
        )
        ledger.add(u1)
        eval_a = evaluate_merge_resolution(
            code_a,
            artifact["agent_a"]["code"],
            artifact["agent_b"]["code"],
            acceptance,
        )
        if eval_a["passed"]:
            break
        code_b, u2 = run_agent_merge_fix(
            agent_id="agent_b",
            file_path=file_path,
            intent=intent_b,
            own_code=code_b,
            peer_code=code_a,
        )
        ledger.add(u2)
        eval_b = evaluate_merge_resolution(
            code_b,
            artifact["agent_a"]["code"],
            artifact["agent_b"]["code"],
            acceptance,
        )
        if eval_b["passed"]:
            code_a = code_b
            break

    final_code = code_a
    evaluation = evaluate_merge_resolution(
        final_code,
        artifact["agent_a"]["code"],
        artifact["agent_b"]["code"],
        acceptance,
    )
    return {
        "path": "baseline",
        "rounds": rounds,
        "final_code": final_code,
        "evaluation": evaluation,
        "usage": ledger.to_dict(),
    }


def run_overlord_path(
    artifact: dict[str, Any],
    acceptance: dict[str, Any],
    ledger: UsageLedger,
    session_id: str,
) -> dict[str, Any]:
    from bedrock import knowledge_base

    kb_context = None
    try:
        kb_context = knowledge_base.get_context_for_agents(
            ["agent_a", "agent_b"],
            module_hint=artifact["file_path"],
            session_id=session_id,
        )
    except Exception:
        kb_context = None

    raw = arbitrate(
        artifact["agent_a"],
        artifact["agent_b"],
        kb_context=kb_context or None,
        conflict_kind="merge",
    )
    usage_meta = raw.pop("_usage", None)
    if usage_meta:
        ledger.add(
            InvokeUsage(
                model_id=usage_meta["model_id"],
                role="overlord",
                input_tokens=usage_meta["input_tokens"],
                output_tokens=usage_meta["output_tokens"],
                latency_ms=usage_meta["latency_ms"],
            )
        )

    final_code = raw.get("resolved_code", "")
    evaluation = evaluate_merge_resolution(
        final_code,
        artifact["agent_a"]["code"],
        artifact["agent_b"]["code"],
        acceptance,
    )
    try:
        mem.log_decision(
            session_id,
            raw.get("reasoning", "overlord merge resolution"),
            ["agent_a", "agent_b"],
        )
    except Exception:
        pass
    return {
        "path": "overlord",
        "rounds": 1,
        "final_code": final_code,
        "resolution": raw,
        "evaluation": evaluation,
        "usage": ledger.to_dict(),
    }


def run_benchmark(
    scenario_name: str,
    *,
    seed_mode: str | None = None,
) -> dict[str, Any]:
    if _live_disabled():
        raise RuntimeError("Live benchmark disabled (LIVE_BENCHMARK_DISABLED=1)")

    scenario = get_merge_scenario(scenario_name)
    acceptance = scenario.get("acceptance", {})
    seed_mode = seed_mode or os.getenv("LIVE_BENCHMARK_SEED_MODE", "scenario")
    session_id = f"live-benchmark-{scenario_name}-{uuid.uuid4().hex[:8]}"

    seed_ledger = UsageLedger()
    artifact = _build_artifact(scenario, seed_mode, seed_ledger)

    baseline_ledger = UsageLedger()
    for call in seed_ledger.calls:
        baseline_ledger.add(call)
    baseline = run_baseline_path(artifact, acceptance, baseline_ledger)

    overlord_ledger = UsageLedger()
    for call in seed_ledger.calls:
        overlord_ledger.add(call)
    overlord = run_overlord_path(artifact, acceptance, overlord_ledger, session_id)

    b_tokens = baseline["usage"]["total_tokens"]
    o_tokens = overlord["usage"]["total_tokens"]
    token_delta = b_tokens - o_tokens
    token_savings_pct = int(100 * token_delta / b_tokens) if b_tokens else 0

    b_ms = baseline["usage"]["total_latency_ms"]
    o_ms = overlord["usage"]["total_latency_ms"]
    time_delta_ms = b_ms - o_ms
    time_savings_pct = int(100 * time_delta_ms / b_ms) if b_ms else 0

    return {
        "scenario": scenario_name,
        "session_id": session_id,
        "seed_mode": seed_mode,
        "max_rounds": MAX_ROUNDS,
        "mock_bedrock": os.getenv("OVERLORD_MOCK_BEDROCK") == "1",
        "artifact": artifact,
        "baseline": baseline,
        "overlord": overlord,
        "comparison": {
            "baseline_passed": baseline["evaluation"]["passed"],
            "overlord_passed": overlord["evaluation"]["passed"],
            "baseline_score": baseline["evaluation"]["score"],
            "overlord_score": overlord["evaluation"]["score"],
            "baseline_tokens": b_tokens,
            "overlord_tokens": o_tokens,
            "token_delta": token_delta,
            "token_savings_pct": token_savings_pct,
            "overlord_beats_tokens": o_tokens < b_tokens,
            **build_cost_comparison(baseline["usage"], overlord["usage"]),
            "overlord_beats_quality": overlord["evaluation"]["score"]
            > baseline["evaluation"]["score"],
            "baseline_resolution_time_ms": b_ms,
            "overlord_resolution_time_ms": o_ms,
            "time_delta_ms": time_delta_ms,
            "time_savings_pct": time_savings_pct,
            "overlord_beats_time": o_ms < b_ms,
        },
    }
