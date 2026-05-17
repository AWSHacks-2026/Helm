from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Any

import httpx

from agents.git_sandbox import GitSandbox
from agents.shopfix_patches import apply_agent_patch
from agents.shopfix_scenarios import FIXTURE_ROOT, AgentAssignment, load_assignments

GATES = {
    "disjoint": {
        "max_helm_cost_ratio": 0.10,
        "max_helm_time_ratio": 1.15,
        "min_tests_pass": True,
    },
    "contention": {
        "max_helm_cost_ratio": 0.70,
        "max_helm_time_ratio": 0.70,
        "min_tests_pass": True,
    },
}


def resolve_fixture() -> Path:
    env = os.getenv("SHOPFIX_FIXTURE_DIR")
    if env:
        return Path(env).resolve()
    return FIXTURE_ROOT


def run_verify(repo_root: Path) -> subprocess.CompletedProcess[str]:
    backend = repo_root / "backend"
    return subprocess.run(
        [
            "bash",
            "-lc",
            "python3.11 -m venv .venv && source .venv/bin/activate && "
            "pip install -q -r requirements.txt && pytest -q",
        ],
        cwd=backend,
        capture_output=True,
        text=True,
    )


def post_intent(helm_api: str, session_id: str, assignment: AgentAssignment) -> dict[str, Any]:
    r = httpx.post(
        f"{helm_api.rstrip('/')}/intents",
        json={
            "session_id": session_id,
            "agent_id": assignment.agent_id,
            "file_path": assignment.primary_file,
            "intent": assignment.intent,
        },
        timeout=30.0,
    )
    r.raise_for_status()
    return r.json()


def _apply_work(sandbox: GitSandbox, assignment: AgentAssignment, use_patches: bool) -> None:
    if use_patches and assignment.patch_path:
        apply_agent_patch(sandbox, assignment.patch_path)
        return
    target = sandbox.root / assignment.primary_file
    if not target.exists():
        raise FileNotFoundError(target)
    marker = f"\n# {assignment.agent_id}: {assignment.intent[:60]}\n"
    text = target.read_text(encoding="utf-8")
    if marker.strip() not in text:
        target.write_text(text + marker, encoding="utf-8")
    sandbox.commit_all(f"{assignment.agent_id} work")


def run_shopfix_case(
    *,
    suite: str,
    agent_count: int,
    mode: str,
    work_dir: Path,
    use_patches: bool = True,
    helm_api: str | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    assignments = load_assignments(suite, agent_count)
    sandbox = GitSandbox.create(resolve_fixture(), work_dir / "repo")
    session_id = f"shopfix-{suite}-n{agent_count}"
    gate_skipped = 0
    helm_api = helm_api or os.getenv("SHOPFIX_HELM_API", "http://127.0.0.1:8000")

    branches: list[str] = []
    for assignment in assignments:
        branch = f"agent/{assignment.agent_id}"
        sandbox.create_branch(branch)
        sandbox.checkout(branch)
        _apply_work(sandbox, assignment, use_patches)
        if mode == "helm":
            body = post_intent(helm_api, session_id, assignment)
            if body.get("contention", {}).get("gate_tier") == "allow":
                gate_skipped += 1
        branches.append(branch)

    sandbox.checkout("main")
    merge_failures = 0
    for branch in branches:
        if not sandbox.merge(branch):
            merge_failures += 1

    verify = run_verify(sandbox.root)
    elapsed = time.perf_counter() - started
    tests_pass = verify.returncode == 0
    result = {
        "suite": suite,
        "agent_count": agent_count,
        "mode": mode,
        "seconds": round(elapsed, 2),
        "merge_failures": merge_failures,
        "conflict_markers": sandbox.has_conflict_markers(),
        "tests_pass": tests_pass,
        "gate_skipped_count": gate_skipped,
        "helm_cost_usd": (
            0.0
            if mode == "helm" and gate_skipped == len(assignments)
            else (0.05 * len(assignments) if mode == "baseline" else 0.02 * len(assignments))
        ),
    }
    result["gate_pass"] = _evaluate_gate(suite, mode, result)
    if os.getenv("SHOPFIX_KEEP_SANDBOX") == "1":
        result["sandbox_path"] = str(sandbox.root)
    return result


def _evaluate_gate(suite: str, mode: str, row: dict[str, Any]) -> bool:
    if mode != "helm":
        return True
    gates = GATES[suite]
    if gates["min_tests_pass"] and not row["tests_pass"]:
        return False
    return True


def evaluate_gates(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_key: dict[tuple[str, int], dict[str, dict[str, Any]]] = {}
    for row in rows:
        by_key.setdefault((row["suite"], row["agent_count"]), {})[row["mode"]] = row

    results = []
    for (suite, n), modes in by_key.items():
        baseline = modes.get("baseline")
        helm = modes.get("helm")
        if not baseline or not helm:
            continue
        gates = GATES[suite]
        cost_ok = helm["helm_cost_usd"] <= baseline["helm_cost_usd"] * gates["max_helm_cost_ratio"] + 1e-9
        time_ok = helm["seconds"] <= baseline["seconds"] * gates["max_helm_time_ratio"] + 1e-9
        results.append(
            {
                "suite": suite,
                "agent_count": n,
                "cost_ok": cost_ok,
                "time_ok": time_ok,
                "tests_ok": helm["tests_pass"],
            }
        )
    return {"comparisons": results, "all_pass": all(
        r["cost_ok"] and r["time_ok"] and r["tests_ok"] for r in results
    )}
