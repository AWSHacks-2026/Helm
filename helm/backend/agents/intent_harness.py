"""Benchmark: agents proceed with conflicting intents vs Helm intent coordination."""

from __future__ import annotations

import os
import time
import uuid
from typing import Any

from agents.haiku_agent import run_agent_edit
from agents.scenarios import get_scenario
from agents.usage_ledger import UsageLedger
from bedrock.cost_estimate import build_cost_comparison
from helm import arbitrate

DEFAULT_SCENARIO = "intent_conflict"


def run_baseline_path(scenario: dict[str, Any], ledger: UsageLedger) -> dict[str, Any]:
    """Both agents implement independently (two Haiku calls, no coordination)."""
    started = time.perf_counter()
    file_path = scenario.get("file_path", "app/services/module.py")
    code_a, usage_a = run_agent_edit(
        agent_id="agent_a",
        file_path=file_path,
        intent=scenario["agent_a"]["intent"],
        peer_code=None,
    )
    ledger.add(usage_a)
    code_b, usage_b = run_agent_edit(
        agent_id="agent_b",
        file_path=file_path,
        intent=scenario["agent_b"]["intent"],
        peer_code=code_a,
    )
    ledger.add(usage_b)
    elapsed_ms = int((time.perf_counter() - started) * 1000)

    return {
        "path": "baseline",
        "agents_proceeding": 2,
        "conflict_detected_before_code": False,
        "unified_intent": None,
        "resolution_time_ms": elapsed_ms,
        "usage": ledger.to_dict(),
    }


def run_helm_path(scenario: dict[str, Any], ledger: UsageLedger) -> dict[str, Any]:
    """One Sonnet call coordinates intents before conflicting implementation."""
    started = time.perf_counter()
    raw = arbitrate(
        scenario["agent_a"],
        scenario["agent_b"],
        kb_context=scenario.get("history"),
        conflict_kind="intent",
        session_id=f"intent-benchmark-{uuid.uuid4().hex[:8]}",
    )
    usage_meta = raw.pop("_usage", None)
    if usage_meta:
        from bedrock.invoke_tracked import InvokeUsage

        ledger.add(
            InvokeUsage(
                model_id=usage_meta["model_id"],
                role="helm-intent",
                input_tokens=usage_meta["input_tokens"],
                output_tokens=usage_meta["output_tokens"],
                latency_ms=usage_meta["latency_ms"],
            )
        )

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    compatibility = raw.get("compatibility", "conflict")

    return {
        "path": "helm",
        "agents_proceeding": 1 if compatibility == "conflict" else 2,
        "conflict_detected_before_code": compatibility == "conflict",
        "unified_intent": raw.get("unified_intent"),
        "resolution": raw,
        "reasoning": raw.get("reasoning"),
        "tokens_saved_estimate": raw.get("tokens_saved_estimate"),
        "resolution_time_ms": elapsed_ms,
        "usage": ledger.to_dict(),
    }


def run_intent_benchmark(scenario_name: str = DEFAULT_SCENARIO) -> dict[str, Any]:
    if scenario_name != DEFAULT_SCENARIO:
        raise ValueError(f"Unknown intent scenario: {scenario_name}")

    scenario = get_scenario(scenario_name)
    session_id = f"intent-benchmark-{scenario_name}-{uuid.uuid4().hex[:8]}"

    baseline_ledger = UsageLedger()
    baseline = run_baseline_path(scenario, baseline_ledger)

    helm_ledger = UsageLedger()
    helm = run_helm_path(scenario, helm_ledger)

    b_tokens = baseline["usage"]["total_tokens"]
    o_tokens = helm["usage"]["total_tokens"]
    token_delta = b_tokens - o_tokens
    token_savings_pct = int(100 * token_delta / b_tokens) if b_tokens else 0

    b_ms = baseline["resolution_time_ms"]
    o_ms = helm["resolution_time_ms"]
    time_delta_ms = b_ms - o_ms
    time_savings_pct = int(100 * time_delta_ms / b_ms) if b_ms else 0

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
            "helm_stops_conflict": helm["conflict_detected_before_code"],
            "baseline_agents_proceeding": baseline["agents_proceeding"],
            "helm_agents_proceeding": helm["agents_proceeding"],
            "helm_beats_cost": helm["usage"]["estimated_cost_usd"]
            < baseline["usage"]["estimated_cost_usd"],
        },
    }
