"""Six-agent merge conflict benchmark: Haiku chain vs Overlord fleet arbitration."""

from __future__ import annotations

import os
import time
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import Any

from agents.haiku_agent import continuation_max_tokens, run_agent_merge_fix
from agents.merge_evaluator import evaluate_merge_resolution
from agents.merge_scenarios import get_merge_scenario
from agents.usage_ledger import UsageLedger
from bedrock.cost_estimate import build_cost_comparison
from bedrock.invoke_tracked import InvokeUsage
from overlord import _arbitrate_file_group, arbitrate_fleet

DEFAULT_SCENARIO = "merge_conflict_fleet"
MAX_ROUNDS = int(os.getenv("LIVE_BASELINE_MAX_ROUNDS", "3"))


def _live_disabled() -> bool:
    return os.getenv("LIVE_BENCHMARK_DISABLED", "0") == "1"


def get_merge_fleet_scenario_names() -> list[str]:
    return ["merge_conflict_fleet"]


def _scenario_agents(scenario: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {aid: dict(payload) for aid, payload in scenario["agents"].items()}


def _agents_grouped_by_file(
    agents: dict[str, dict[str, Any]],
    file_paths: dict[str, str],
) -> dict[str, list[tuple[str, dict[str, Any]]]]:
    grouped: dict[str, list[tuple[str, dict[str, Any]]]] = defaultdict(list)
    for agent_id in sorted(agents):
        grouped[file_paths[agent_id]].append((agent_id, agents[agent_id]))
    return dict(grouped)


def _evaluate_file(
    resolved_code: str,
    agent_list: list[tuple[str, dict[str, Any]]],
    acceptance: dict[str, Any],
) -> dict[str, Any]:
    first_code = agent_list[0][1]["code"]
    last_code = agent_list[-1][1]["code"]
    return evaluate_merge_resolution(
        resolved_code,
        first_code,
        last_code,
        acceptance,
    )


def run_baseline_path(
    scenario: dict[str, Any],
    grouped: dict[str, list[tuple[str, dict[str, Any]]]],
    acceptance_by_file: dict[str, dict[str, Any]],
    ledger: UsageLedger,
) -> dict[str, Any]:
    """Agents sequentially merge-fix on each shared file (no Overlord)."""
    started = time.perf_counter()
    file_results: dict[str, Any] = {}
    merge_fix_calls = 0
    token_cap = continuation_max_tokens()

    for file_path, agent_list in grouped.items():
        acceptance = acceptance_by_file.get(file_path, {})
        code = agent_list[0][1]["code"]
        rounds = 0

        for _round in range(MAX_ROUNDS):
            rounds += 1
            for agent_id, agent in agent_list[1:]:
                code, usage = run_agent_merge_fix(
                    agent_id=agent_id,
                    file_path=file_path,
                    intent=agent["intent"],
                    own_code=code,
                    peer_code=agent["code"],
                )
                ledger.add(usage)
                merge_fix_calls += 1
            evaluation = _evaluate_file(code, agent_list, acceptance)
            if evaluation["passed"]:
                break

        file_results[file_path] = {
            "final_code": code,
            "rounds": rounds,
            "evaluation": _evaluate_file(code, agent_list, acceptance),
        }

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    scores = [fr["evaluation"]["score"] for fr in file_results.values()]
    passed_all = all(fr["evaluation"]["passed"] for fr in file_results.values())

    return {
        "path": "baseline",
        "merge_fix_calls": merge_fix_calls,
        "files_merged": len(file_results),
        "rounds_max": MAX_ROUNDS,
        "resolution_time_ms": elapsed_ms,
        "mean_score": int(sum(scores) / len(scores)) if scores else 0,
        "passed_all": passed_all,
        "files": file_results,
        "usage": ledger.to_dict(),
    }


def _fleet_merge_strategy() -> str:
    return os.getenv("MERGE_FLEET_STRATEGY", "haiku_chain").strip().lower()


def _merge_file_haiku_chain(
    file_path: str,
    agent_list: list[tuple[str, dict[str, Any]]],
    ledger: UsageLedger,
    ledger_lock: Lock | None = None,
    *,
    max_rounds: int = 1,
) -> dict[str, Any]:
    if len(agent_list) == 1:
        return {
            "file_path": file_path,
            "resolved_code": agent_list[0][1]["code"],
            "merge_fix_calls": 0,
            "reasoning": "Single agent on file; no merge required.",
        }

    code = agent_list[0][1]["code"]
    merge_fix_calls = 0
    for _round in range(max_rounds):
        for agent_id, agent in agent_list[1:]:
            code, usage = run_agent_merge_fix(
                agent_id=agent_id,
                file_path=file_path,
                intent=agent["intent"],
                own_code=code,
                peer_code=agent["code"],
            )
            if ledger_lock:
                with ledger_lock:
                    ledger.add(usage)
            else:
                ledger.add(usage)
            merge_fix_calls += 1

    return {
        "file_path": file_path,
        "resolved_code": code,
        "merge_fix_calls": merge_fix_calls,
        "reasoning": (
            f"Haiku merge-fix chain ({merge_fix_calls} call(s), one round) on {file_path}."
        ),
    }


def _run_haiku_fleet_merge(
    agents: dict[str, dict[str, Any]],
    file_paths: dict[str, str],
    grouped: dict[str, list[tuple[str, dict[str, Any]]]],
    acceptance_by_file: dict[str, dict[str, Any]],
    ledger: UsageLedger,
) -> dict[str, Any]:
    """One Haiku merge-fix round per conflicted file (parallel), same model as baseline agents."""
    paths = sorted(grouped.keys())
    parallel = os.getenv("MERGE_FLEET_PARALLEL", "1") == "1"
    ledger_lock = Lock() if parallel and len(paths) > 1 else None
    max_rounds = int(os.getenv("MERGE_FLEET_HAIKU_ROUNDS", "1"))

    def merge_one(path: str) -> dict[str, Any]:
        return _merge_file_haiku_chain(
            path,
            grouped[path],
            ledger,
            ledger_lock,
            max_rounds=max_rounds,
        )

    if parallel and len(paths) > 1:
        with ThreadPoolExecutor(max_workers=len(paths)) as pool:
            futures = {pool.submit(merge_one, path): path for path in paths}
            ordered: dict[str, dict[str, Any]] = {}
            for future in as_completed(futures):
                path = futures[future]
                ordered[path] = future.result()
            merges = [ordered[path] for path in paths]
    else:
        merges = [merge_one(path) for path in paths]

    total_merge_calls = sum(m["merge_fix_calls"] for m in merges)
    reasonings = [f"{m['file_path']}: {m['reasoning']}" for m in merges if m.get("reasoning")]

    file_results: dict[str, Any] = {}
    for item in merges:
        file_path = item["file_path"]
        agent_list = grouped[file_path]
        acceptance = acceptance_by_file.get(file_path, {})
        file_results[file_path] = {
            "final_code": item["resolved_code"],
            "rounds": max_rounds,
            "evaluation": _evaluate_file(item["resolved_code"], agent_list, acceptance),
        }

    escalate = os.getenv("MERGE_FLEET_ESCALATE_SONNET", "0") == "1"
    sonnet_calls = 0
    if escalate:
        for file_path, fr in list(file_results.items()):
            if fr["evaluation"]["passed"]:
                continue
            # One extra Haiku round before paying for Sonnet
            extra = _merge_file_haiku_chain(
                file_path,
                grouped[file_path],
                ledger,
                ledger_lock,
                max_rounds=1,
            )
            code = extra["resolved_code"]
            agent_list = grouped[file_path]
            acceptance = acceptance_by_file.get(file_path, {})
            retry_eval = _evaluate_file(code, agent_list, acceptance)
            file_results[file_path] = {
                "final_code": code,
                "rounds": max_rounds + 1,
                "evaluation": retry_eval,
            }
            if retry_eval["passed"]:
                continue
            agents_on_file = {aid: agent for aid, agent in grouped[file_path]}
            sonnet_item = _arbitrate_file_group(file_path, agents_on_file)
            usage_meta = sonnet_item.pop("_usage", None)
            if usage_meta:
                ledger.add(
                    InvokeUsage(
                        model_id=usage_meta["model_id"],
                        role=f"overlord-merge-{file_path.replace('/', '-')}",
                        input_tokens=usage_meta["input_tokens"],
                        output_tokens=usage_meta["output_tokens"],
                        latency_ms=usage_meta["latency_ms"],
                    )
                )
                sonnet_calls += 1
            if sonnet_item.get("reasoning"):
                reasonings.append(f"{file_path}: {sonnet_item['reasoning']}")
            code = sonnet_item["resolved_code"]
            agent_list = grouped[file_path]
            acceptance = acceptance_by_file.get(file_path, {})
            file_results[file_path] = {
                "final_code": code,
                "rounds": max_rounds + 1,
                "evaluation": _evaluate_file(code, agent_list, acceptance),
            }

    resolutions = [
        {"file_path": path, "resolved_code": file_results[path]["final_code"]}
        for path in paths
    ]
    arbitration_calls = total_merge_calls + sonnet_calls

    return {
        "conflict_type": "merge_conflict",
        "resolutions": resolutions,
        "reasoning": " ".join(reasonings),
        "arbitration_calls": arbitration_calls,
        "haiku_merge_calls": total_merge_calls,
        "sonnet_escalation_calls": sonnet_calls,
        "parallel": parallel,
        "strategy": "haiku_chain",
        "files": file_results,
    }


def run_overlord_path(
    scenario: dict[str, Any],
    agents: dict[str, dict[str, Any]],
    file_paths: dict[str, str],
    grouped: dict[str, list[tuple[str, dict[str, Any]]]],
    acceptance_by_file: dict[str, dict[str, Any]],
    ledger: UsageLedger,
) -> dict[str, Any]:
    started = time.perf_counter()
    strategy = _fleet_merge_strategy()

    if strategy == "sonnet":
        raw = arbitrate_fleet(agents, file_paths)
        usage_meta = raw.pop("_usage", None)
        if usage_meta:
            ledger.add(
                InvokeUsage(
                    model_id=usage_meta["model_id"],
                    role="overlord-merge-fleet",
                    input_tokens=usage_meta["input_tokens"],
                    output_tokens=usage_meta["output_tokens"],
                    latency_ms=usage_meta["latency_ms"],
                )
            )
        file_results: dict[str, Any] = {}
        for item in raw.get("resolutions", []):
            file_path = item["file_path"]
            code = item["resolved_code"]
            agent_list = grouped[file_path]
            acceptance = acceptance_by_file.get(file_path, {})
            file_results[file_path] = {
                "final_code": code,
                "rounds": 1,
                "evaluation": _evaluate_file(code, agent_list, acceptance),
            }
        raw["strategy"] = "sonnet"
    else:
        raw = _run_haiku_fleet_merge(agents, file_paths, grouped, acceptance_by_file, ledger)
        file_results = raw.pop("files")

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    scores = [fr["evaluation"]["score"] for fr in file_results.values()]
    passed_all = all(fr["evaluation"]["passed"] for fr in file_results.values())

    return {
        "path": "overlord",
        "strategy": raw.get("strategy", strategy),
        "arbitration_calls": raw.get("arbitration_calls", 1),
        "haiku_merge_calls": raw.get("haiku_merge_calls"),
        "sonnet_escalation_calls": raw.get("sonnet_escalation_calls", 0),
        "parallel": raw.get("parallel", True),
        "files_merged": len(file_results),
        "resolution_time_ms": elapsed_ms,
        "mean_score": int(sum(scores) / len(scores)) if scores else 0,
        "passed_all": passed_all,
        "files": file_results,
        "resolution": raw,
        "reasoning": raw.get("reasoning"),
        "usage": ledger.to_dict(),
    }


def run_merge_fleet_benchmark(
    scenario_name: str = DEFAULT_SCENARIO,
) -> dict[str, Any]:
    if _live_disabled():
        raise RuntimeError("Live benchmark disabled (LIVE_BENCHMARK_DISABLED=1)")

    if scenario_name not in get_merge_fleet_scenario_names():
        raise ValueError(f"Unknown merge fleet scenario: {scenario_name}")

    scenario = get_merge_scenario(scenario_name)
    agents = _scenario_agents(scenario)
    file_paths = dict(scenario["file_paths"])
    acceptance_by_file = dict(scenario.get("acceptance_by_file", {}))
    grouped = _agents_grouped_by_file(agents, file_paths)
    session_id = f"merge-fleet-{scenario_name}-{uuid.uuid4().hex[:8]}"

    baseline_ledger = UsageLedger()
    baseline = run_baseline_path(scenario, grouped, acceptance_by_file, baseline_ledger)

    overlord_ledger = UsageLedger()
    overlord = run_overlord_path(
        scenario, agents, file_paths, grouped, acceptance_by_file, overlord_ledger
    )

    b_tokens = baseline["usage"]["total_tokens"]
    o_tokens = overlord["usage"]["total_tokens"]
    token_delta = b_tokens - o_tokens
    token_savings_pct = int(100 * token_delta / b_tokens) if b_tokens else 0

    b_ms = baseline["resolution_time_ms"]
    o_ms = overlord["resolution_time_ms"]
    time_delta_ms = b_ms - o_ms
    time_savings_pct = int(100 * time_delta_ms / b_ms) if b_ms else 0

    merge_calls_saved = baseline["merge_fix_calls"] - overlord.get("arbitration_calls", 1)

    return {
        "scenario": scenario_name,
        "session_id": session_id,
        "agent_count": len(agents),
        "file_paths": file_paths,
        "token_limits": {
            "merge_max_tokens": continuation_max_tokens(),
            "strategy": _fleet_merge_strategy(),
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
            "baseline_merge_fix_calls": baseline["merge_fix_calls"],
            "overlord_arbitration_calls": overlord["arbitration_calls"],
            "merge_fix_calls_avoided": max(0, merge_calls_saved),
            "baseline_mean_score": baseline["mean_score"],
            "overlord_mean_score": overlord["mean_score"],
            "overlord_beats_quality": overlord["mean_score"] >= baseline["mean_score"],
            "baseline_passed_all": baseline["passed_all"],
            "overlord_passed_all": overlord["passed_all"],
        },
    }
