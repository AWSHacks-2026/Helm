"""ShopFix git + merge fleet: baseline Haiku merge chain vs parallel per-file fleet merge."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from agents.merge_fleet_harness import _run_haiku_fleet_merge, run_baseline_path
from agents.shopfix_live_benchmark import (
    _run_agents_parallel,
    resolve_fixture,
    run_verify,
)
from agents.shopfix_scenarios import AgentAssignment, load_assignments
from agents.usage_ledger import UsageLedger
from bedrock.cost_estimate import build_cost_comparison
from agents.git_sandbox import GitSandbox


def _maybe_verify(repo_root: Path) -> subprocess.CompletedProcess[str]:
    if os.getenv("SHOPFIX_SKIP_VERIFY", "0") == "1":
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    return run_verify(repo_root)


def _grouped_from_assignments(
    assignments: list[AgentAssignment],
    sandbox: GitSandbox,
) -> dict[str, list[tuple[str, dict[str, Any]]]]:
    grouped: dict[str, list[tuple[str, dict[str, Any]]]] = defaultdict(list)
    for agent in assignments:
        code = sandbox.show_file(f"agent/{agent.agent_id}", agent.primary_file)
        grouped[agent.primary_file].append(
            (agent.agent_id, {"intent": agent.intent, "code": code})
        )
    return {path: agents for path, agents in grouped.items() if len(agents) >= 2}


def _agents_and_paths(
    assignments: list[AgentAssignment],
    sandbox: GitSandbox,
) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    agents: dict[str, dict[str, Any]] = {}
    paths: dict[str, str] = {}
    for agent in assignments:
        paths[agent.agent_id] = agent.primary_file
        agents[agent.agent_id] = {
            "intent": agent.intent,
            "code": sandbox.show_file(f"agent/{agent.agent_id}", agent.primary_file),
        }
    return agents, paths


def _clone_repo(src: Path, dst: Path) -> GitSandbox:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    return GitSandbox(root=dst)


def _apply_resolutions(sandbox: GitSandbox, resolutions: dict[str, str]) -> None:
    sandbox.checkout("main")
    for rel_path, code in resolutions.items():
        sandbox.write_file(rel_path, code)
        sandbox._run("git", "add", rel_path)
    sandbox._run(
        "git",
        "-c",
        "user.email=helm@shopfix.test",
        "-c",
        "user.name=Helm",
        "commit",
        "-m",
        "merge resolution",
    )


def prepare_shopfix_agent_branches(
    suite: str,
    agent_count: int,
    work_dir: Path,
) -> tuple[
    GitSandbox,
    list[AgentAssignment],
    dict[str, list[tuple[str, dict[str, Any]]]],
]:
    """All agents implement on branches; contested files = multi-agent merge input."""
    assignments = load_assignments(suite, agent_count)
    prep_dir = work_dir / "prep-repo"
    sandbox = GitSandbox.create(resolve_fixture(), prep_dir)
    _run_agents_parallel(sandbox, assignments, UsageLedger())
    grouped = _grouped_from_assignments(assignments, sandbox)
    if not grouped:
        raise RuntimeError(
            f"No multi-agent files (suite={suite} N={agent_count}); use contention with N>=4"
        )
    return sandbox, assignments, grouped


def run_shopfix_merge_fleet_benchmark(
    suite: str = "contention",
    agent_count: int = 6,
    work_dir: Path | None = None,
) -> dict[str, Any]:
    if os.getenv("LIVE_BENCHMARK_DISABLED", "0") == "1":
        raise RuntimeError("LIVE_BENCHMARK_DISABLED=1")

    from tempfile import mkdtemp

    base = work_dir or Path(mkdtemp(prefix="shopfix-merge-fleet-"))
    base.mkdir(parents=True, exist_ok=True)

    prep, assignments, grouped = prepare_shopfix_agent_branches(
        suite, agent_count, base
    )
    agents, file_paths = _agents_and_paths(assignments, prep)
    acceptance_by_file: dict[str, dict[str, Any]] = {}
    pseudo_scenario: dict[str, Any] = {"agents": agents}

    # Baseline: sequential Haiku merge-fix chain per file (merge_fleet harness)
    baseline_sandbox = _clone_repo(prep.root, base / "baseline-merge")
    baseline_ledger = UsageLedger()
    baseline = run_baseline_path(
        pseudo_scenario, grouped, acceptance_by_file, baseline_ledger
    )
    resolutions_b = {
        path: fr["final_code"] for path, fr in baseline["files"].items()
    }
    _apply_resolutions(baseline_sandbox, resolutions_b)
    baseline_verify = _maybe_verify(baseline_sandbox.root)

    # Helm: parallel per-file Haiku fleet merge (default MERGE_FLEET_STRATEGY=haiku_chain)
    helm_sandbox = _clone_repo(prep.root, base / "helm-merge")
    helm_ledger = UsageLedger()
    helm_started = time.perf_counter()
    raw = _run_haiku_fleet_merge(
        agents, file_paths, grouped, acceptance_by_file, helm_ledger
    )
    helm_ms = int((time.perf_counter() - helm_started) * 1000)
    resolutions_h = {
        item["file_path"]: item["resolved_code"] for item in raw.get("resolutions", [])
    }
    _apply_resolutions(helm_sandbox, resolutions_h)
    helm_verify = _maybe_verify(helm_sandbox.root)

    scores_h = [fr["evaluation"]["score"] for fr in raw["files"].values()]
    helm = {
        "path": "helm_fleet",
        "strategy": raw.get("strategy", "haiku_chain"),
        "arbitration_calls": raw.get("arbitration_calls", 0),
        "haiku_merge_calls": raw.get("haiku_merge_calls", 0),
        "parallel": raw.get("parallel", True),
        "resolution_time_ms": helm_ms,
        "mean_score": int(sum(scores_h) / len(scores_h)) if scores_h else 0,
        "passed_all": all(fr["evaluation"]["passed"] for fr in raw["files"].values()),
        "usage": helm_ledger.to_dict(),
        "tests_pass": helm_verify.returncode == 0,
    }

    baseline["tests_pass"] = baseline_verify.returncode == 0
    comparison = build_cost_comparison(baseline["usage"], helm["usage"])
    b_ms = baseline["resolution_time_ms"]
    h_ms = helm["resolution_time_ms"]
    comparison["baseline_resolution_time_ms"] = b_ms
    comparison["helm_resolution_time_ms"] = h_ms
    comparison["time_delta_ms"] = b_ms - h_ms
    comparison["time_savings_pct"] = int(100 * (b_ms - h_ms) / b_ms) if b_ms else 0
    comparison["helm_beats_time"] = h_ms < b_ms
    comparison["baseline_merge_fix_calls"] = baseline["merge_fix_calls"]
    comparison["helm_arbitration_calls"] = helm["arbitration_calls"]
    comparison["baseline_tests_pass"] = baseline["tests_pass"]
    comparison["helm_tests_pass"] = helm["tests_pass"]
    comparison["baseline_mean_score"] = baseline["mean_score"]
    comparison["helm_mean_score"] = helm["mean_score"]

    return {
        "suite": suite,
        "agent_count": agent_count,
        "fixture": str(resolve_fixture()),
        "mock_bedrock": os.getenv("HELM_MOCK_BEDROCK") == "1",
        "merge_fleet_strategy": os.getenv("MERGE_FLEET_STRATEGY", "haiku_chain"),
        "merge_fleet_parallel": os.getenv("MERGE_FLEET_PARALLEL", "1") == "1",
        "token_limits": {
            "live_agent_max_tokens": int(os.getenv("LIVE_AGENT_MAX_TOKENS", "800")),
            "merge_fleet_max_tokens": int(
                os.getenv("MERGE_FLEET_MAX_TOKENS", os.getenv("LIVE_AGENT_MAX_TOKENS", "4096"))
            ),
        },
        "contested_files": list(grouped.keys()),
        "agents_per_file": {k: len(v) for k, v in grouped.items()},
        "baseline": baseline,
        "helm": helm,
        "comparison": comparison,
    }


def format_shopfix_merge_summary(result: dict[str, Any]) -> str:
    c = result["comparison"]
    return (
        f"shopfix merge fleet [{result['suite']} N={result['agent_count']}] "
        f"files={result['contested_files']}\n"
        f"  baseline: {c['baseline_cost_display']} / {c['baseline_resolution_time_ms']}ms "
        f"({c['baseline_merge_fix_calls']} merge-fix) pytest={c['baseline_tests_pass']}\n"
        f"  helm:     {c['helm_cost_display']} / {c['helm_resolution_time_ms']}ms "
        f"({c['helm_arbitration_calls']} fleet calls, parallel={result['merge_fleet_parallel']}) "
        f"pytest={c['helm_tests_pass']}\n"
        f"  savings:  {c['cost_savings_pct']}% cost, {c['time_savings_pct']}% wall"
    )
