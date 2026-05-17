from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import httpx


@dataclass
class RunReport:
    run_id: str
    suite: str
    helm_enabled: bool
    wall_clock_seconds: float
    helm_api_calls: int
    intents_declared: int
    guardrails_blocked: int
    conflicts_resolved: int
    git_conflict_files: int
    merge_success: bool
    agent_commits: list[str]
    tokens_saved_display: str


def _count_events(history: list[dict[str, Any]], event_type: str) -> int:
    return sum(1 for e in history if e.get("event_type") == event_type)


def collect_run(
    *,
    run_id: str,
    results_dir: Path,
    api_base: str,
    session_id: str,
    integration_repo: Path | None = None,
) -> RunReport:
    meta_path = results_dir / run_id / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    started = float(meta.get("started_at", 0))
    ended = float(meta.get("ended_at", started))
    wall_clock = max(0.0, ended - started)

    with httpx.Client(base_url=api_base, timeout=30.0) as client:
        history = client.get("/history", params={"session_id": session_id}).json()
        gratitude = client.get("/gratitude", params={"session_id": session_id}).json()

    helm_api_calls = len(history) + (1 if gratitude else 0)
    intents_declared = _count_events(history, "intent_declared")
    guardrails_blocked = _count_events(history, "guardrail_blocked")
    conflicts_resolved = _count_events(history, "conflict_resolved")
    tokens_saved_display = str(gratitude.get("tokens_saved_display", gratitude.get("summary", "n/a")))

    agent_commits: list[str] = []
    merge_success = bool(meta.get("merge_success", False))
    git_conflict_files = int(meta.get("git_conflict_files", 0))
    if integration_repo and (integration_repo / ".git").exists():
        log = subprocess.run(
            ["git", "log", "--oneline", "-20"],
            cwd=integration_repo,
            capture_output=True,
            text=True,
            check=False,
        )
        agent_commits = [line.strip() for line in log.stdout.splitlines() if line.strip()]

    report = RunReport(
        run_id=run_id,
        suite=meta.get("suite", "unknown"),
        helm_enabled=bool(meta.get("helm_enabled", True)),
        wall_clock_seconds=wall_clock,
        helm_api_calls=helm_api_calls,
        intents_declared=intents_declared,
        guardrails_blocked=guardrails_blocked,
        conflicts_resolved=conflicts_resolved,
        git_conflict_files=git_conflict_files,
        merge_success=merge_success,
        agent_commits=agent_commits,
        tokens_saved_display=tokens_saved_display,
    )
    out_dir = results_dir / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.json").write_text(
        json.dumps(asdict(report), indent=2),
        encoding="utf-8",
    )
    return report
