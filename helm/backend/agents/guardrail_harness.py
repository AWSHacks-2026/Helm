"""Benchmark: unchecked destructive action vs Helm guardrail preflight + resolution."""

from __future__ import annotations

import os
import time
import uuid
from typing import Any

from agents.haiku_agent import run_agent_edit
from agents.usage_ledger import UsageLedger
from bedrock import guardrails
from bedrock.cost_estimate import build_cost_comparison
from bedrock.guardrails import GUARDRAIL_DEMO_SCENARIO, seed_guardrail_demo

DEFAULT_SCENARIO = "guardrail_prevention"


def run_baseline_path(scenario: dict[str, Any], ledger: UsageLedger) -> dict[str, Any]:
    """Destructive delete runs, then peer rebuilds (no preflight)."""
    started = time.perf_counter()
    proposed = scenario["proposed_action"]
    file_path = proposed["file_path"]

    _, usage_delete = run_agent_edit(
        agent_id=proposed["agent_id"],
        file_path=file_path,
        intent=proposed["description"],
        peer_code=None,
    )
    ledger.add(usage_delete)

    _, usage_rebuild = run_agent_edit(
        agent_id="agent_a",
        file_path=file_path,
        intent=scenario["agent_a"]["intent"],
        peer_code=None,
    )
    ledger.add(usage_rebuild)

    elapsed_ms = int((time.perf_counter() - started) * 1000)

    return {
        "path": "baseline",
        "executed": True,
        "preflight_allowed": True,
        "blocked_rule": None,
        "resolution": None,
        "resolution_time_ms": elapsed_ms,
        "usage": ledger.to_dict(),
    }


def run_helm_path(
    scenario: dict[str, Any],
    session_id: str,
    ledger: UsageLedger,
) -> dict[str, Any]:
    os.environ["HELM_USE_LOCAL_MEMORY"] = "true"
    os.environ["HELM_USE_LOCAL_POLICY"] = "true"

    started = time.perf_counter()
    seed_guardrail_demo(session_id=session_id)
    result = guardrails.handle_proposed_action(
        scenario["proposed_action"],
        scenario["agent_a"],
        scenario["agent_b"],
        session_id=session_id,
    )

    resolution = dict(result.get("resolution") or {})
    usage_meta = resolution.pop("_usage", None)
    resolution_tier = result.get("resolution_tier") or resolution.get("resolution_tier")
    escalated = result.get("escalated_to_sonnet", False)
    if usage_meta:
        from bedrock.invoke_tracked import InvokeUsage

        ledger.add(
            InvokeUsage(
                model_id=usage_meta["model_id"],
                role="helm-guardrail",
                input_tokens=usage_meta["input_tokens"],
                output_tokens=usage_meta["output_tokens"],
                latency_ms=usage_meta["latency_ms"],
            )
        )

    elapsed_ms = int((time.perf_counter() - started) * 1000)

    return {
        "path": "helm",
        "executed": result.get("executed", False),
        "preflight_allowed": result["preflight"]["allowed"],
        "blocked_rule": result["preflight"].get("rule"),
        "resolution": resolution if resolution else None,
        "verdict": result.get("verdict") or resolution.get("verdict"),
        "resolution_tier": resolution_tier,
        "escalated_to_sonnet": escalated,
        "resolution_time_ms": elapsed_ms,
        "usage": ledger.to_dict(),
    }


def run_guardrail_fleet_benchmark() -> dict[str, Any]:
    """Five-agent fleet guardrail (routes to Sonnet via GUARDRAIL_SONNET_MIN_AGENTS)."""
    from bedrock.guardrails import (
        GUARDRAIL_FLEET_SCENARIO,
        seed_guardrail_fleet_demo,
    )

    scenario = GUARDRAIL_FLEET_SCENARIO
    session_id = f"guardrail-fleet-benchmark-{uuid.uuid4().hex[:8]}"

    os.environ["HELM_USE_LOCAL_MEMORY"] = "true"
    os.environ["HELM_USE_LOCAL_POLICY"] = "true"

    started = time.perf_counter()
    seed_guardrail_fleet_demo(session_id=session_id)
    result = guardrails.handle_proposed_action_fleet(
        scenario["proposed_action"],
        scenario["agents"],
        session_id=session_id,
    )
    elapsed_ms = int((time.perf_counter() - started) * 1000)

    resolution = dict(result.get("resolution") or {})
    usage_meta = resolution.pop("_usage", None)
    ledger = UsageLedger()
    if usage_meta:
        from bedrock.invoke_tracked import InvokeUsage

        ledger.add(
            InvokeUsage(
                model_id=usage_meta["model_id"],
                role="helm-guardrail-fleet",
                input_tokens=usage_meta["input_tokens"],
                output_tokens=usage_meta["output_tokens"],
                latency_ms=usage_meta["latency_ms"],
            )
        )

    return {
        "scenario": "guardrail_fleet",
        "session_id": session_id,
        "mock_bedrock": os.getenv("HELM_MOCK_BEDROCK") == "1",
        "agent_count": len(scenario["agents"]),
        "helm": {
            "path": "helm",
            "executed": result.get("executed", False),
            "preflight_allowed": result["preflight"]["allowed"],
            "blocked_rule": result["preflight"].get("rule"),
            "resolution": resolution or None,
            "verdict": result.get("verdict"),
            "resolution_tier": result.get("resolution_tier"),
            "escalated_to_sonnet": result.get("escalated_to_sonnet", False),
            "resolution_time_ms": elapsed_ms,
            "usage": ledger.to_dict(),
        },
    }


def run_guardrail_benchmark(scenario_name: str = DEFAULT_SCENARIO) -> dict[str, Any]:
    if scenario_name != DEFAULT_SCENARIO:
        raise ValueError(f"Unknown guardrail scenario: {scenario_name}")

    scenario = GUARDRAIL_DEMO_SCENARIO
    session_id = f"guardrail-benchmark-{uuid.uuid4().hex[:8]}"

    baseline_ledger = UsageLedger()
    baseline = run_baseline_path(scenario, baseline_ledger)

    helm_ledger = UsageLedger()
    helm = run_helm_path(scenario, session_id, helm_ledger)

    b_tokens = baseline["usage"]["total_tokens"]
    o_tokens = helm["usage"]["total_tokens"]
    token_delta = b_tokens - o_tokens
    token_savings_pct = int(100 * token_delta / b_tokens) if b_tokens else 0

    b_ms = baseline["resolution_time_ms"]
    o_ms = helm["resolution_time_ms"]
    time_delta_ms = b_ms - o_ms
    time_savings_pct = int(100 * time_delta_ms / b_ms) if b_ms else 0

    b_cost = baseline["usage"]["estimated_cost_usd"]
    o_cost = helm["usage"]["estimated_cost_usd"]

    return {
        "scenario": scenario_name,
        "session_id": session_id,
        "mock_bedrock": os.getenv("HELM_MOCK_BEDROCK") == "1",
        "baseline": baseline,
        "helm": helm,
        "comparison": {
            "baseline_tokens": b_tokens,
            "helm_tokens": o_tokens,
            "token_delta": token_delta,
            "token_savings_pct": token_savings_pct,
            "helm_beats_tokens": o_tokens < b_tokens,
            **build_cost_comparison(baseline["usage"], helm["usage"]),
            "baseline_resolution_time_ms": b_ms,
            "helm_resolution_time_ms": o_ms,
            "time_delta_ms": time_delta_ms,
            "time_savings_pct": time_savings_pct,
            "helm_beats_time": o_ms < b_ms,
            "baseline_executed": baseline["executed"],
            "helm_executed": helm["executed"],
            "helm_blocked_action": not helm["preflight_allowed"],
            "blocked_rule": helm.get("blocked_rule"),
            "helm_beats_cost": o_cost < b_cost if b_cost else False,
            "resolution_tier": helm.get("resolution_tier"),
            "escalated_to_sonnet": helm.get("escalated_to_sonnet"),
        },
    }
