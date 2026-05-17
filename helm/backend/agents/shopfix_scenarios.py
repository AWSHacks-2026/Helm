from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from agents.live_matrix.scenarios import WorkAssignment, assign_work, load_tasks

FIXTURE_ROOT = Path(__file__).resolve().parents[3] / "shopfix"
SCENARIO_DIR = FIXTURE_ROOT / "scenarios"


@dataclass
class AgentAssignment:
    agent_id: str
    primary_file: str
    intent: str
    patch_path: Path | None = None
    task_id: str | None = None


def _agent_id(index: int) -> str:
    return f"agent_{chr(ord('a') + index)}"


def load_work_assignments(suite: str, agent_count: int) -> list[WorkAssignment]:
    tasks = load_tasks(SCENARIO_DIR)
    return assign_work(tasks, suite, agent_count)


def load_assignments(suite: str, agent_count: int) -> list[AgentAssignment]:
    """Backward-compatible: one assignment per agent (first task only)."""
    work = load_work_assignments(suite, agent_count)
    by_agent: dict[str, list[WorkAssignment]] = {}
    for item in work:
        by_agent.setdefault(item.agent_id, []).append(item)
    out: list[AgentAssignment] = []
    for i in range(agent_count):
        aid = _agent_id(i)
        tasks = by_agent.get(aid, [])
        if not tasks:
            continue
        first = tasks[0]
        patch = _patch_path(suite, agent_count, aid)
        out.append(
            AgentAssignment(
                agent_id=aid,
                primary_file=first.primary_file,
                intent=first.intent,
                patch_path=patch if patch.exists() else None,
                task_id=first.task_id,
            )
        )
    return out


def _patch_path(suite: str, agent_count: int, agent_id: str) -> Path:
    return FIXTURE_ROOT / "patches" / suite / f"n{agent_count}" / f"{agent_id}.patch"
