from __future__ import annotations

from pathlib import Path

from agents.live_matrix.scenarios import WorkAssignment, assign_work, load_tasks

FIXTURE_ROOT = Path(__file__).resolve().parents[3] / "streamcast"
SCENARIO_DIR = FIXTURE_ROOT / "scenarios"


def load_work_assignments(suite: str, agent_count: int) -> list[WorkAssignment]:
    tasks = load_tasks(SCENARIO_DIR)
    return assign_work(tasks, suite, agent_count)
