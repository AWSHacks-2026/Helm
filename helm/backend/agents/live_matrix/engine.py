"""Shared live benchmark engine: multi-task queues, git, Bedrock, optional Helm."""

from __future__ import annotations

import os
import subprocess
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from agents.git_sandbox import GitSandbox
from agents.haiku_agent import reassign_max_tokens, run_agent_edit, run_agent_merge_fix
from agents.live_matrix.helm_client import HelmClient
from agents.live_matrix.progress import TimestepTracker
from agents.live_matrix.scenarios import WorkAssignment, assign_work, group_by_agent, load_tasks
from agents.live_matrix.task_queue import build_agent_queues
from agents.usage_ledger import UsageLedger
from bedrock.contention_gate import assess_dedup, gate_enabled, gate_force, skipped_dedup_result
from bedrock.invoke_tracked import InvokeUsage
from helm import detect_duplication, detect_duplication_fleet
from store.sessions import SessionStore


@dataclass(frozen=True)
class LiveAppConfig:
    app_name: str
    fixture_root: Path
    scenario_dir: Path
    session_prefix: str
    verify: Callable[[Path], subprocess.CompletedProcess[str]]


def _run_dedup(agents_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    ids = list(agents_by_id.keys())
    if len(ids) < 2:
        return skipped_dedup_result(ids)
    if len(ids) == 2:
        return detect_duplication(agents_by_id[ids[0]], agents_by_id[ids[1]])
    return detect_duplication_fleet(agents_by_id)


def _record_dedup_usage(ledger: UsageLedger, raw: dict[str, Any], *, fleet: bool) -> None:
    usage_meta = raw.pop("_usage", None)
    if not usage_meta:
        return
    ledger.add(
        InvokeUsage(
            model_id=usage_meta["model_id"],
            role="helm-dedup-fleet" if fleet else "helm-dedup",
            input_tokens=usage_meta["input_tokens"],
            output_tokens=usage_meta["output_tokens"],
            latency_ms=usage_meta["latency_ms"],
        )
    )


def _agents_by_file(assignments: list[WorkAssignment]) -> dict[str, list[WorkAssignment]]:
    by_file: dict[str, list[WorkAssignment]] = defaultdict(list)
    for item in assignments:
        by_file[item.primary_file].append(item)
    return dict(by_file)


def _agents_map_from_queues(
    sandbox: GitSandbox,
    queues: dict[str, list[WorkAssignment]],
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for aid, tasks in queues.items():
        if not tasks:
            continue
        first = tasks[0]
        rel = first.primary_file
        code = sandbox.read_file(rel) if (sandbox.root / rel).exists() else ""
        intents = "; ".join(t.intent for t in tasks)
        out[aid] = {
            "intent": intents,
            "code": code,
            "proposed_action": intents,
        }
    return out


def _execute_task_on_branch(
    sandbox: GitSandbox,
    work: WorkAssignment,
    ledger: UsageLedger,
    tracker: TimestepTracker,
    *,
    helm: HelmClient | None,
    peer_code: str | None,
    reassignment: bool = False,
) -> str | None:
    branch = f"agent/{work.agent_id}"
    sandbox.checkout(branch)
    rel = work.primary_file
    if not (sandbox.root / rel).exists():
        tracker.record_timestep(phase=f"{work.agent_id}:{work.task_id}:skip_missing")
        return None
    current = sandbox.read_file(rel)
    if helm:
        helm.declare_intent(work.agent_id, rel, work.intent)
        tracker.record_timestep(phase=f"{work.agent_id}:{work.task_id}:intent", input_tokens=0, output_tokens=0, latency_ms=0)
    max_tokens = reassign_max_tokens() if reassignment else None
    code, usage = run_agent_edit(
        agent_id=work.agent_id,
        file_path=rel,
        intent=work.intent,
        peer_code=peer_code or current,
        max_tokens=max_tokens,
    )
    ledger.add(usage)
    tracker.record_usage(usage, phase=f"{work.agent_id}:{work.task_id}:edit")
    if helm:
        check = helm.guardrail_check(work.agent_id, rel, code)
        tracker.record_timestep(
            phase=f"{work.agent_id}:{work.task_id}:guardrail",
            input_tokens=0,
            output_tokens=0,
            latency_ms=0,
        )
        if not check.get("allowed", True):
            return None
    sandbox.write_file(rel, code)
    sandbox.commit_all(f"feat({work.agent_id}): {work.task_id}")
    tracker.record_timestep(phase=f"{work.agent_id}:{work.task_id}:commit", input_tokens=0, output_tokens=0, latency_ms=0)
    return code


def _run_task_queues(
    sandbox: GitSandbox,
    queues: dict[str, list[WorkAssignment]],
    ledger: UsageLedger,
    tracker: TimestepTracker,
    *,
    helm: HelmClient | None,
    continuations: list[str] | None = None,
    reassignments: list[dict[str, str]] | None = None,
) -> int:
    """Run agent task queues; returns commit count."""
    commits = 0
    latest_by_file: dict[str, str] = {}
    active_agents = set(continuations) if continuations is not None else set(queues.keys())
    reassignment_map = {r["agent_id"]: r.get("suggested_new_task", "") for r in (reassignments or [])}

    for agent_id in sorted(active_agents):
        tasks = list(queues.get(agent_id, []))
        if not tasks:
            continue
        sandbox.checkout("main")
        sandbox.create_branch(f"agent/{agent_id}")
        for work in tasks:
            intent = work.intent
            if agent_id in reassignment_map and reassignment_map[agent_id]:
                work = WorkAssignment(
                    agent_id=work.agent_id,
                    task_id=work.task_id,
                    primary_file=work.primary_file,
                    intent=reassignment_map[agent_id],
                )
            peer = latest_by_file.get(work.primary_file)
            code = _execute_task_on_branch(
                sandbox,
                work,
                ledger,
                tracker,
                helm=helm,
                peer_code=peer,
                reassignment=agent_id in reassignment_map,
            )
            if code is not None:
                latest_by_file[work.primary_file] = code
                commits += 1
    return commits


def _merge_all_branches(sandbox: GitSandbox, branch_names: list[str]) -> int:
    sandbox.checkout("main")
    failures = 0
    seen: set[str] = set()
    for branch in branch_names:
        if branch in seen:
            continue
        seen.add(branch)
        if not sandbox.merge(branch):
            failures += 1
    return failures


def _resolve_file_conflicts(
    sandbox: GitSandbox,
    rel_path: str,
    agents_on_file: list[WorkAssignment],
    ledger: UsageLedger,
    tracker: TimestepTracker,
) -> None:
    if len(agents_on_file) < 2:
        return
    first, second = agents_on_file[0], agents_on_file[1]
    own = sandbox.show_file(f"agent/{first.agent_id}", rel_path)
    peer = sandbox.show_file(f"agent/{second.agent_id}", rel_path)
    merged, usage = run_agent_merge_fix(
        agent_id=first.agent_id,
        file_path=rel_path,
        intent=first.intent,
        own_code=own,
        peer_code=peer,
    )
    ledger.add(usage)
    tracker.record_usage(usage, phase=f"merge_fix:{rel_path}")
    sandbox.write_file(rel_path, merged)
    sandbox._run("git", "add", rel_path)
    sandbox._run(
        "git",
        "-c",
        "user.email=helm@shopfix.test",
        "-c",
        "user.name=Helm",
        "commit",
        "-m",
        f"resolve {rel_path}",
    )


def _finish_sandbox(
    sandbox: GitSandbox,
    assignments: list[WorkAssignment],
    ledger: UsageLedger,
    tracker: TimestepTracker,
    started: float,
    config: LiveAppConfig,
    *,
    helm_stats: dict | None,
) -> dict[str, Any]:
    by_file = _agents_by_file(assignments)
    for rel_path in sandbox.conflicted_paths():
        _resolve_file_conflicts(sandbox, rel_path, by_file.get(rel_path, []), ledger, tracker)

    if sandbox.has_conflict_markers():
        for rel_path, agents_on_file in by_file.items():
            if len(agents_on_file) >= 2:
                _resolve_file_conflicts(sandbox, rel_path, agents_on_file, ledger, tracker)

    verify = config.verify(sandbox.root)
    usage = ledger.to_dict()
    sonnet_calls = sum(
        1 for c in usage.get("calls", []) if "sonnet" in c.get("model_id", "").lower()
    )
    dedup_calls = sum(1 for c in usage.get("calls", []) if "dedup" in c.get("role", ""))

    result: dict[str, Any] = {
        "app": config.app_name,
        "seconds": round(time.perf_counter() - started, 2),
        "tests_pass": verify.returncode == 0,
        "verify_stdout": verify.stdout[-500:] if verify.stdout else "",
        "verify_stderr": verify.stderr[-500:] if verify.stderr else "",
        "usage": usage,
        "estimated_cost_usd": usage.get("estimated_cost_usd", 0),
        "sonnet_calls": sonnet_calls,
        "dedup_calls": dedup_calls,
        "haiku_calls": usage.get("call_count", 0) - sonnet_calls,
        "tasks_total": len(assignments),
    }
    if helm_stats:
        result["helm"] = helm_stats
    if os.getenv("SHOPFIX_KEEP_SANDBOX") == "1" or os.getenv("LIVE_MATRIX_KEEP_SANDBOX") == "1":
        result["sandbox_path"] = str(sandbox.root)
    return result


def load_assignments_for_run(
    config: LiveAppConfig,
    suite: str,
    agent_count: int,
) -> list[WorkAssignment]:
    tasks = load_tasks(config.scenario_dir)
    return assign_work(tasks, suite, agent_count)


def run_baseline_live(
    config: LiveAppConfig,
    suite: str,
    agent_count: int,
    work_dir: Path,
    tracker: TimestepTracker | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    ledger = UsageLedger()
    assignments = load_assignments_for_run(config, suite, agent_count)
    queues = build_agent_queues(assignments)
    total_steps = sum(len(q) for q in queues.values()) * 3 + 5
    local_tracker = tracker or TimestepTracker(
        desc=f"{config.app_name} baseline {suite} n{agent_count}",
        total_timesteps=total_steps,
    )
    own_tracker = tracker is None

    sandbox = GitSandbox.create(config.fixture_root, work_dir / "baseline-repo")
    commits = _run_task_queues(sandbox, queues, ledger, local_tracker, helm=None)
    branches = [f"agent/{aid}" for aid in queues if queues[aid]]
    _merge_all_branches(sandbox, branches)
    result = _finish_sandbox(sandbox, assignments, ledger, local_tracker, started, config, helm_stats=None)
    result["path"] = "baseline"
    result["suite"] = suite
    result["agent_count"] = agent_count
    result["commits_total"] = commits
    if own_tracker:
        local_tracker.close()
    return result


def run_helm_live(
    config: LiveAppConfig,
    suite: str,
    agent_count: int,
    work_dir: Path,
    *,
    helm_api_base: str = "http://127.0.0.1:8000",
    tracker: TimestepTracker | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    ledger = UsageLedger()
    assignments = load_assignments_for_run(config, suite, agent_count)
    queues = build_agent_queues(assignments)
    total_steps = sum(len(q) for q in queues.values()) * 5 + 10
    local_tracker = tracker or TimestepTracker(
        desc=f"{config.app_name} helm {suite} n{agent_count}",
        total_timesteps=total_steps,
    )
    own_tracker = tracker is None

    session_id = f"{config.session_prefix}-{suite}-n{agent_count}"
    helm = HelmClient(base_url=helm_api_base, session_id=session_id)

    sandbox = GitSandbox.create(config.fixture_root, work_dir / "helm-repo")
    agents_by_id = _agents_map_from_queues(sandbox, queues)
    file_paths = {aid: (queues[aid][0].primary_file if queues[aid] else "") for aid in queues}

    gate_store = SessionStore()
    for aid, payload in agents_by_id.items():
        gate_store.record_intent(
            session_id=session_id,
            agent_id=aid,
            file_path=file_paths[aid],
            intent=payload["intent"],
        )

    gate_skipped = False
    gate_assessment: dict[str, Any] | None = None
    continuations: list[str] = []
    reassignments: list[dict[str, str]] = []

    try:
        if gate_enabled() and not gate_force():
            assessment = assess_dedup(
                gate_store, session_id, agents=agents_by_id, file_paths=file_paths
            )
            gate_assessment = assessment.to_dict()
            if assessment.gate_tier == "allow":
                gate_skipped = True
                continuations = list(agents_by_id.keys())
            else:
                raw = _run_dedup(agents_by_id)
                _record_dedup_usage(ledger, raw, fleet=len(agents_by_id) >= 3)
                local_tracker.record_timestep(phase="dedup", input_tokens=0, output_tokens=0, latency_ms=0)
                continuations = list(raw.get("continuations") or [])
                reassignments = list(raw.get("reassignments") or [])
                if not continuations and raw.get("duplicate_detected"):
                    continuations = [raw.get("agent_to_continue", "agent_a")]
                    reassignments = [
                        {
                            "agent_id": raw.get("agent_to_reassign", "agent_b"),
                            "suggested_new_task": raw.get("suggested_new_task", ""),
                        }
                    ]
        else:
            raw = _run_dedup(agents_by_id)
            _record_dedup_usage(ledger, raw, fleet=len(agents_by_id) >= 3)
            local_tracker.record_timestep(phase="dedup", input_tokens=0, output_tokens=0, latency_ms=0)
            continuations = list(raw.get("continuations") or list(agents_by_id.keys()))
            reassignments = list(raw.get("reassignments") or [])

        commits = _run_task_queues(
            sandbox,
            queues,
            ledger,
            local_tracker,
            helm=helm,
            continuations=continuations,
            reassignments=reassignments,
        )
        helm_branches = [f"agent/{aid}" for aid in continuations if aid in queues and queues[aid]]
        for item in reassignments:
            aid = item.get("agent_id")
            if aid and aid in queues and queues[aid]:
                helm_branches.append(f"agent/{aid}")
        _merge_all_branches(sandbox, list(dict.fromkeys(helm_branches)))
        helm_stats = helm.stats()
        helm_stats.update(
            {
                "gate_skipped": gate_skipped,
                "gate_assessment": gate_assessment,
                "continuations": continuations,
                "reassignments": reassignments,
            }
        )
        result = _finish_sandbox(
            sandbox, assignments, ledger, local_tracker, started, config, helm_stats=helm_stats
        )
        result["path"] = "helm"
        result["suite"] = suite
        result["agent_count"] = agent_count
        result["commits_total"] = commits
        result["gate_skipped"] = gate_skipped
        result["gate_assessment"] = gate_assessment
        result["continuations"] = continuations
        result["reassignments"] = reassignments
    finally:
        helm.close()
        if own_tracker:
            local_tracker.close()
    return result


def run_live_pair(
    config: LiveAppConfig,
    suite: str,
    agent_count: int,
    work_dir: Path,
    *,
    helm_api_base: str = "http://127.0.0.1:8000",
) -> dict[str, Any]:
    from bedrock.cost_estimate import build_cost_comparison

    baseline = run_baseline_live(config, suite, agent_count, work_dir)
    helm = run_helm_live(config, suite, agent_count, work_dir, helm_api_base=helm_api_base)
    comparison = build_cost_comparison(baseline["usage"], helm["usage"])
    comparison["baseline_seconds"] = baseline["seconds"]
    comparison["helm_seconds"] = helm["seconds"]
    comparison["time_savings_pct"] = (
        int(100 * (baseline["seconds"] - helm["seconds"]) / baseline["seconds"])
        if baseline["seconds"] > 0
        else 0
    )
    comparison["baseline_tests_pass"] = baseline["tests_pass"]
    comparison["helm_tests_pass"] = helm["tests_pass"]
    comparison["helm_gate_skipped"] = helm.get("gate_skipped")
    comparison["baseline_sonnet_calls"] = baseline.get("sonnet_calls", 0)
    comparison["helm_sonnet_calls"] = helm.get("sonnet_calls", 0)
    comparison["helm_dedup_calls"] = helm.get("dedup_calls", 0)
    return {
        "app": config.app_name,
        "suite": suite,
        "agent_count": agent_count,
        "fixture": str(config.fixture_root),
        "mock_bedrock": os.getenv("HELM_MOCK_BEDROCK", "0") == "1",
        "baseline": baseline,
        "helm": helm,
        "comparison": comparison,
    }
