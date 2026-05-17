"""Compare baseline duplicate agent work vs Overlord task deduplication."""

from __future__ import annotations

import os
import time
import uuid
from typing import Any

from agents.haiku_agent import (
    continuation_max_tokens,
    reassign_max_tokens,
    run_agent_edit,
)
from agents.scenarios import get_scenario
from agents.usage_ledger import UsageLedger
from bedrock.cost_estimate import build_cost_comparison
from bedrock.invoke_tracked import InvokeUsage
from overlord import detect_duplication, detect_duplication_fleet

DEFAULT_SCENARIO = "duplicate_work_fleet"
DEFAULT_FILE = "app/auth/handlers.py"
PAIRWISE_SCENARIOS = frozenset({"duplicate_work"})


def _live_disabled() -> bool:
    return os.getenv("LIVE_BENCHMARK_DISABLED", "0") == "1"


def get_dedup_scenario_names() -> list[str]:
    return ["duplicate_work", "duplicate_work_fleet"]


def _scenario_agents(scenario: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    if "agents" in scenario:
        return [(aid, dict(payload)) for aid, payload in scenario["agents"].items()]
    return [
        ("agent_a", dict(scenario["agent_a"])),
        ("agent_b", dict(scenario["agent_b"])),
    ]


def _scenario_file_paths(scenario: dict[str, Any]) -> dict[str, str]:
    if "file_paths" in scenario:
        return dict(scenario["file_paths"])
    default = scenario.get("file_path", DEFAULT_FILE)
    return {aid: default for aid, _ in _scenario_agents(scenario)}


def _implementation_prompt(agent: dict[str, Any]) -> str:
    action = agent.get("proposed_action") or agent["intent"]
    return (
        f"{agent['intent']}\n\n"
        f"Implement this now in the target file:\n{action}\n\n"
        "Output complete Python for the module."
    )


def _reassignment_prompt(task: str) -> str:
    return (
        f"Focused follow-up task (do not rebuild the whole module):\n{task}\n\n"
        "Add only the code needed for this task. Prefer a small patch (~80 lines max). "
        "Integrate with the peer code below if present."
    )


def _run_haiku_implementation(
    *,
    agent_id: str,
    file_path: str,
    agent: dict[str, Any],
    peer_code: str | None,
    ledger: UsageLedger,
    max_tokens: int | None = None,
    reassignment: bool = False,
) -> str:
    if reassignment:
        task = agent.get("proposed_action") or agent["intent"]
        intent = _reassignment_prompt(task)
        token_cap = max_tokens if max_tokens is not None else reassign_max_tokens()
    else:
        intent = _implementation_prompt(agent)
        token_cap = max_tokens if max_tokens is not None else continuation_max_tokens()

    code, usage = run_agent_edit(
        agent_id=agent_id,
        file_path=file_path,
        intent=intent,
        peer_code=peer_code,
        max_tokens=token_cap,
    )
    ledger.add(usage)
    return code


def _count_full_runs(agent_order: list[str], continuations: set[str]) -> int:
    return len(continuations)


def run_baseline_path(
    scenario: dict[str, Any],
    file_paths: dict[str, str],
    ledger: UsageLedger,
) -> dict[str, Any]:
    """Every agent fully implements its assigned task (no Overlord)."""
    started = time.perf_counter()
    agents = _scenario_agents(scenario)
    implementations: dict[str, str] = {}
    latest_by_file: dict[str, str] = {}

    for agent_id, agent in agents:
        file_path = file_paths[agent_id]
        peer_code = latest_by_file.get(file_path)
        code = _run_haiku_implementation(
            agent_id=agent_id,
            file_path=file_path,
            agent=agent,
            peer_code=peer_code,
            ledger=ledger,
        )
        implementations[agent_id] = code
        latest_by_file[file_path] = code

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    agent_count = len(agents)

    return {
        "path": "baseline",
        "duplicate_detected": None,
        "full_implementation_runs": agent_count,
        "agents_executed": agent_count,
        "resolution_time_ms": elapsed_ms,
        "implementations": implementations,
        "usage": ledger.to_dict(),
    }


def _run_agents_from_plan(
    *,
    scenario: dict[str, Any],
    file_paths: dict[str, str],
    continuations: list[str],
    reassignments: list[dict[str, str]],
    agents_by_id: dict[str, dict[str, Any]],
    ledger: UsageLedger,
) -> tuple[dict[str, str], int]:
    implementations: dict[str, str] = {}
    latest_by_file: dict[str, str] = {}
    continuation_set = set(continuations)

    for agent_id in continuations:
        agent = agents_by_id[agent_id]
        file_path = file_paths[agent_id]
        code = _run_haiku_implementation(
            agent_id=agent_id,
            file_path=file_path,
            agent=agent,
            peer_code=latest_by_file.get(file_path),
            ledger=ledger,
        )
        implementations[agent_id] = code
        latest_by_file[file_path] = code

    for item in reassignments:
        agent_id = item["agent_id"]
        agent = agents_by_id[agent_id]
        file_path = file_paths[agent_id]
        task = item["suggested_new_task"]
        payload = {
            **agent,
            "intent": task,
            "proposed_action": task,
        }
        peer = latest_by_file.get(file_path)
        code = _run_haiku_implementation(
            agent_id=agent_id,
            file_path=file_path,
            agent=payload,
            peer_code=peer,
            ledger=ledger,
            reassignment=True,
        )
        implementations[agent_id] = code
        latest_by_file[file_path] = code

    full_runs = _count_full_runs(list(agents_by_id), continuation_set)
    return implementations, full_runs


def run_overlord_path(
    scenario: dict[str, Any],
    file_paths: dict[str, str],
    ledger: UsageLedger,
    scenario_name: str,
) -> dict[str, Any]:
    started = time.perf_counter()
    agents = _scenario_agents(scenario)
    agents_by_id = dict(agents)
    agent_ids = list(agents_by_id.keys())

    if scenario_name in PAIRWISE_SCENARIOS:
        raw = detect_duplication(agents_by_id["agent_a"], agents_by_id["agent_b"])
    else:
        raw = detect_duplication_fleet(agents_by_id)

    usage_meta = raw.pop("_usage", None)
    if usage_meta:
        role = (
            "overlord-dedup-fleet"
            if scenario_name not in PAIRWISE_SCENARIOS
            else "overlord-dedup"
        )
        ledger.add(
            InvokeUsage(
                model_id=usage_meta["model_id"],
                role=role,
                input_tokens=usage_meta["input_tokens"],
                output_tokens=usage_meta["output_tokens"],
                latency_ms=usage_meta["latency_ms"],
            )
        )

    if not raw.get("duplicate_detected"):
        implementations, full_runs = _run_agents_from_plan(
            scenario=scenario,
            file_paths=file_paths,
            continuations=agent_ids,
            reassignments=[],
            agents_by_id=agents_by_id,
            ledger=ledger,
        )
        fleet_meta: dict[str, Any] = {}
    elif "continuations" in raw:
        implementations, full_runs = _run_agents_from_plan(
            scenario=scenario,
            file_paths=file_paths,
            continuations=raw["continuations"],
            reassignments=raw.get("reassignments", []),
            agents_by_id=agents_by_id,
            ledger=ledger,
        )
        fleet_meta = {
            "continuations": raw["continuations"],
            "reassignments": raw.get("reassignments", []),
        }
    else:
        continue_key = raw["agent_to_continue"]
        reassign_key = raw["agent_to_reassign"]
        reassignments = [
            {
                "agent_id": reassign_key,
                "suggested_new_task": raw.get("suggested_new_task", ""),
            }
        ]
        implementations, full_runs = _run_agents_from_plan(
            scenario=scenario,
            file_paths=file_paths,
            continuations=[continue_key],
            reassignments=reassignments,
            agents_by_id=agents_by_id,
            ledger=ledger,
        )
        fleet_meta = {
            "agent_to_continue": continue_key,
            "agent_to_reassign": reassign_key,
            "suggested_new_task": raw.get("suggested_new_task"),
        }

    elapsed_ms = int((time.perf_counter() - started) * 1000)

    return {
        "path": "overlord",
        "duplicate_detected": raw.get("duplicate_detected"),
        "full_implementation_runs": full_runs,
        "agents_executed": len(agent_ids),
        "resolution_time_ms": elapsed_ms,
        "implementations": implementations,
        "dedup_resolution": raw,
        "reasoning": raw.get("reasoning"),
        **fleet_meta,
        "usage": ledger.to_dict(),
    }


def run_dedup_benchmark(
    scenario_name: str = DEFAULT_SCENARIO,
) -> dict[str, Any]:
    if _live_disabled():
        raise RuntimeError("Live benchmark disabled (LIVE_BENCHMARK_DISABLED=1)")

    if scenario_name not in get_dedup_scenario_names():
        raise ValueError(f"Unknown dedup scenario: {scenario_name}")

    scenario = get_scenario(scenario_name)
    file_paths = _scenario_file_paths(scenario)
    session_id = f"dedup-benchmark-{scenario_name}-{uuid.uuid4().hex[:8]}"

    baseline_ledger = UsageLedger()
    baseline = run_baseline_path(scenario, file_paths, baseline_ledger)

    overlord_ledger = UsageLedger()
    overlord = run_overlord_path(scenario, file_paths, overlord_ledger, scenario_name)

    b_tokens = baseline["usage"]["total_tokens"]
    o_tokens = overlord["usage"]["total_tokens"]
    token_delta = b_tokens - o_tokens
    token_savings_pct = int(100 * token_delta / b_tokens) if b_tokens else 0

    b_ms = baseline["resolution_time_ms"]
    o_ms = overlord["resolution_time_ms"]
    time_delta_ms = b_ms - o_ms
    time_savings_pct = int(100 * time_delta_ms / b_ms) if b_ms else 0

    duplicate_runs_saved = (
        baseline["full_implementation_runs"] - overlord["full_implementation_runs"]
    )

    return {
        "scenario": scenario_name,
        "session_id": session_id,
        "agent_count": len(_scenario_agents(scenario)),
        "file_paths": file_paths,
        "token_limits": {
            "continuation_max_tokens": continuation_max_tokens(),
            "reassign_max_tokens": reassign_max_tokens(),
        },
        "mock_bedrock": os.getenv("OVERLORD_MOCK_BEDROCK") == "1",
        "baseline": baseline,
        "overlord": overlord,
        "comparison": {
            "baseline_tokens": b_tokens,
            "overlord_tokens": o_tokens,
            "token_delta": token_delta,
            "token_savings_pct": token_savings_pct,
            "overlord_beats_tokens": o_tokens < b_tokens,
            **build_cost_comparison(baseline["usage"], overlord["usage"]),
            "baseline_resolution_time_ms": b_ms,
            "overlord_resolution_time_ms": o_ms,
            "time_delta_ms": time_delta_ms,
            "time_savings_pct": time_savings_pct,
            "overlord_beats_time": o_ms < b_ms,
            "baseline_full_implementation_runs": baseline["full_implementation_runs"],
            "overlord_full_implementation_runs": overlord["full_implementation_runs"],
            "duplicate_implementations_avoided": duplicate_runs_saved,
            "overlord_duplicate_detected": overlord.get("duplicate_detected"),
        },
    }
