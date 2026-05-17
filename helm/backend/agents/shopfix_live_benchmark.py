"""ShopFix live benchmark: real git + real Bedrock (Haiku agents, Sonnet dedup) + UsageLedger."""

from __future__ import annotations

import os
import subprocess
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from agents.git_sandbox import GitSandbox
from agents.haiku_agent import (
    reassign_max_tokens,
    run_agent_edit,
    run_agent_merge_fix,
)
from agents.shopfix_scenarios import FIXTURE_ROOT, AgentAssignment, load_assignments
from agents.usage_ledger import UsageLedger
from bedrock.contention_gate import assess_dedup, gate_enabled, gate_force
from bedrock.cost_estimate import build_cost_comparison, cost_from_usage, format_usd
from bedrock.invoke_tracked import InvokeUsage
from helm import detect_duplication, detect_duplication_fleet
from store.sessions import SessionStore


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


def resolve_fixture() -> Path:
    env = os.getenv("SHOPFIX_FIXTURE_DIR")
    if env:
        return Path(env).resolve()
    return FIXTURE_ROOT


def run_verify(repo_root: Path) -> subprocess.CompletedProcess[str]:
    backend = repo_root / "backend"
    venv_python = backend / ".venv" / "bin" / "python"
    if venv_python.exists():
        cmd = "source .venv/bin/activate && pytest -q"
    else:
        cmd = (
            "python3.11 -m venv .venv && source .venv/bin/activate && "
            "pip install -q -r requirements.txt && pytest -q"
        )
    return subprocess.run(
        ["bash", "-lc", cmd],
        cwd=backend,
        capture_output=True,
        text=True,
    )


def _agents_by_file(assignments: list[AgentAssignment]) -> dict[str, list[AgentAssignment]]:
    by_file: dict[str, list[AgentAssignment]] = defaultdict(list)
    for a in assignments:
        by_file[a.primary_file].append(a)
    return dict(by_file)


def _agents_map_from_assignments(
    sandbox: GitSandbox, assignments: list[AgentAssignment]
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for a in assignments:
        rel = a.primary_file
        code = sandbox.read_file(rel) if (sandbox.root / rel).exists() else ""
        out[a.agent_id] = {
            "intent": a.intent,
            "code": code,
            "proposed_action": a.intent,
        }
    return out


def _implement_on_branch(
    sandbox: GitSandbox,
    assignment: AgentAssignment,
    ledger: UsageLedger,
    *,
    peer_code: str | None,
    reassignment: bool = False,
) -> str:
    branch = f"agent/{assignment.agent_id}"
    sandbox.checkout(branch)
    rel = assignment.primary_file
    current = sandbox.read_file(rel)
    max_tokens = reassign_max_tokens() if reassignment else None
    code, usage = run_agent_edit(
        agent_id=assignment.agent_id,
        file_path=rel,
        intent=assignment.intent,
        peer_code=peer_code or current,
        max_tokens=max_tokens,
    )
    ledger.add(usage)
    sandbox.write_file(rel, code)
    sandbox.commit_all(f"{assignment.agent_id} implementation")
    return code


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
    agents_on_file: list[AgentAssignment],
    ledger: UsageLedger,
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
    assignments: list[AgentAssignment],
    ledger: UsageLedger,
    started: float,
) -> dict[str, Any]:
    by_file = _agents_by_file(assignments)
    for rel_path in sandbox.conflicted_paths():
        _resolve_file_conflicts(sandbox, rel_path, by_file.get(rel_path, []), ledger)

    if sandbox.has_conflict_markers():
        for rel_path, agents_on_file in by_file.items():
            if len(agents_on_file) >= 2:
                _resolve_file_conflicts(sandbox, rel_path, agents_on_file, ledger)

    verify = run_verify(sandbox.root)
    usage = ledger.to_dict()
    sonnet_calls = sum(
        1 for c in usage.get("calls", []) if "sonnet" in c.get("model_id", "").lower()
    )
    dedup_calls = sum(1 for c in usage.get("calls", []) if "dedup" in c.get("role", ""))

    return {
        "seconds": round(time.perf_counter() - started, 2),
        "tests_pass": verify.returncode == 0,
        "verify_stdout": verify.stdout[-500:] if verify.stdout else "",
        "verify_stderr": verify.stderr[-500:] if verify.stderr else "",
        "usage": usage,
        "estimated_cost_usd": usage.get("estimated_cost_usd", 0),
        "sonnet_calls": sonnet_calls,
        "dedup_calls": dedup_calls,
        "haiku_calls": usage.get("call_count", 0) - sonnet_calls,
    }


def run_baseline_live(
    suite: str,
    agent_count: int,
    work_dir: Path,
) -> dict[str, Any]:
    """Every agent implements on its branch; merge; Haiku merge-fix if needed."""
    started = time.perf_counter()
    ledger = UsageLedger()
    assignments = load_assignments(suite, agent_count)
    sandbox = GitSandbox.create(resolve_fixture(), work_dir / "baseline-repo")
    latest_by_file: dict[str, str] = {}

    for assignment in assignments:
        branch = f"agent/{assignment.agent_id}"
        sandbox.checkout("main")
        sandbox.create_branch(branch)
        peer = latest_by_file.get(assignment.primary_file)
        code = _implement_on_branch(sandbox, assignment, ledger, peer_code=peer)
        latest_by_file[assignment.primary_file] = code

    branches = [f"agent/{a.agent_id}" for a in assignments]
    _merge_all_branches(sandbox, branches)
    result = _finish_sandbox(sandbox, assignments, ledger, started)
    result["path"] = "baseline"
    result["suite"] = suite
    result["agent_count"] = agent_count
    result["full_implementation_runs"] = len(assignments)
    if os.getenv("SHOPFIX_KEEP_SANDBOX") == "1":
        result["sandbox_path"] = str(sandbox.root)
    return result


def run_helm_live(
    suite: str,
    agent_count: int,
    work_dir: Path,
) -> dict[str, Any]:
    """Helm dedup (Sonnet) when gate says arbitrate; fewer Haiku runs; git merge."""
    started = time.perf_counter()
    ledger = UsageLedger()
    assignments = load_assignments(suite, agent_count)
    sandbox = GitSandbox.create(resolve_fixture(), work_dir / "helm-repo")
    session_id = f"shopfix-live-{suite}-n{agent_count}"

    agents_by_id = _agents_map_from_assignments(sandbox, assignments)
    file_paths = {a.agent_id: a.primary_file for a in assignments}

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
        continuations = list(raw.get("continuations") or list(agents_by_id.keys()))
        reassignments = list(raw.get("reassignments") or [])

    assignment_by_id = {a.agent_id: a for a in assignments}
    latest_by_file: dict[str, str] = {}

    for aid in continuations:
        a = assignment_by_id[aid]
        sandbox.checkout("main")
        sandbox.create_branch(f"agent/{aid}")
        peer = latest_by_file.get(a.primary_file)
        code = _implement_on_branch(sandbox, a, ledger, peer_code=peer)
        latest_by_file[a.primary_file] = code

    for item in reassignments:
        aid = item["agent_id"]
        a = assignment_by_id.get(aid)
        if not a:
            continue
        task = item.get("suggested_new_task") or a.intent
        reassigned = AgentAssignment(
            agent_id=a.agent_id,
            primary_file=a.primary_file,
            intent=task,
            patch_path=a.patch_path,
        )
        sandbox.checkout("main")
        sandbox.create_branch(f"agent/{aid}")
        peer = latest_by_file.get(a.primary_file)
        code = _implement_on_branch(
            sandbox, reassigned, ledger, peer_code=peer, reassignment=True
        )
        latest_by_file[a.primary_file] = code

    helm_branches = [f"agent/{aid}" for aid in continuations if aid in assignment_by_id]
    for item in reassignments:
        aid = item.get("agent_id")
        if aid and aid in assignment_by_id:
            helm_branches.append(f"agent/{aid}")
    _merge_all_branches(sandbox, helm_branches)
    result = _finish_sandbox(sandbox, assignments, ledger, started)
    result["path"] = "helm"
    result["suite"] = suite
    result["agent_count"] = agent_count
    result["gate_skipped"] = gate_skipped
    result["gate_assessment"] = gate_assessment
    result["full_implementation_runs"] = len(continuations) + len(reassignments)
    result["continuations"] = continuations
    result["reassignments"] = reassignments
    if os.getenv("SHOPFIX_KEEP_SANDBOX") == "1":
        result["sandbox_path"] = str(sandbox.root)
    return result


def run_shopfix_live_pair(
    suite: str,
    agent_count: int,
    work_dir: Path,
) -> dict[str, Any]:
    if os.getenv("LIVE_BENCHMARK_DISABLED", "0") == "1":
        raise RuntimeError("LIVE_BENCHMARK_DISABLED=1")

    baseline = run_baseline_live(suite, agent_count, work_dir)
    helm = run_helm_live(suite, agent_count, work_dir)
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
        "suite": suite,
        "agent_count": agent_count,
        "fixture": str(resolve_fixture()),
        "mock_bedrock": os.getenv("HELM_MOCK_BEDROCK", "0") == "1",
        "baseline": baseline,
        "helm": helm,
        "comparison": comparison,
    }


def format_summary(result: dict[str, Any]) -> str:
    c = result["comparison"]
    lines = [
        f"ShopFix LIVE — {result['suite']} — N={result['agent_count']}",
        f"  mock_bedrock={result['mock_bedrock']}",
        f"  baseline: {c['baseline_cost_display']} / {c['baseline_seconds']}s "
        f"sonnet={c.get('baseline_sonnet_calls', 0)} tests={c['baseline_tests_pass']}",
        f"  helm:     {c['helm_cost_display']} / {c['helm_seconds']}s "
        f"sonnet={c.get('helm_sonnet_calls', 0)} dedup={c.get('helm_dedup_calls', 0)} "
        f"gate_skipped={c.get('helm_gate_skipped')} tests={c['helm_tests_pass']}",
        f"  savings:  {c['cost_savings_pct']}% cost, {c['time_savings_pct']}% time",
    ]
    return "\n".join(lines)
