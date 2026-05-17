from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class TaskDef:
    task_id: str
    intent: str
    hotspot_group: str | None
    primary_file: str
    disjoint_alt_file: str | None
    ui_accent: str | None = None


@dataclass(frozen=True)
class WorkAssignment:
    agent_id: str
    task_id: str
    primary_file: str
    intent: str


def agent_id(index: int) -> str:
    return f"agent_{chr(ord('a') + index)}"


def agent_ids(count: int) -> list[str]:
    if count < 1:
        raise ValueError("agent_count must be >= 1")
    return [agent_id(i) for i in range(count)]


def load_tasks(scenario_dir: Path) -> list[TaskDef]:
    raw = yaml.safe_load((scenario_dir / "tasks.yaml").read_text(encoding="utf-8"))
    tasks: list[TaskDef] = []
    for item in raw["tasks"]:
        files = item["files"]
        tasks.append(
            TaskDef(
                task_id=item["task_id"],
                intent=item["intent"],
                hotspot_group=item.get("hotspot_group"),
                primary_file=files["primary"],
                disjoint_alt_file=files.get("disjoint_alt"),
                ui_accent=item.get("ui_accent"),
            )
        )
    if len(tasks) != 10:
        raise ValueError(f"expected 10 tasks, got {len(tasks)}")
    return tasks


def load_suite_policy(scenario_dir: Path, suite: str) -> dict[str, Any]:
    return yaml.safe_load((scenario_dir / f"{suite}.yaml").read_text(encoding="utf-8"))


def _intent_for_agent(task: TaskDef, aid: str) -> str:
    intent = task.intent
    if task.ui_accent:
        accent = _accent_for_agent(aid, task.ui_accent)
        intent = intent.replace("{agent_accent}", accent)
    return intent


def _accent_for_agent(aid: str, template: str) -> str:
    palette = ["#e74c3c", "#3498db", "#2ecc71", "#9b59b6", "#f39c12", "#1abc9c", "#e91e63", "#00bcd4"]
    idx = ord(aid[-1]) - ord("a")
    color = palette[idx % len(palette)]
    return template.replace("{color}", color) if "{color}" in template else color


def assign_work(
    tasks: list[TaskDef],
    suite: str,
    agent_count: int,
    *,
    policy: dict[str, Any] | None = None,
) -> list[WorkAssignment]:
    aids = agent_ids(agent_count)
    assignments: list[WorkAssignment] = []
    if suite == "disjoint":
        for i, task in enumerate(tasks):
            aid = aids[i % len(aids)]
            if task.hotspot_group and task.disjoint_alt_file:
                path = task.disjoint_alt_file
            else:
                path = task.primary_file
            assignments.append(
                WorkAssignment(
                    agent_id=aid,
                    task_id=task.task_id,
                    primary_file=path,
                    intent=_intent_for_agent(task, aid),
                )
            )
        return assignments

    if suite == "contention":
        hotspot_groups: dict[str, list[TaskDef]] = {}
        non_hotspot: list[TaskDef] = []
        for task in tasks:
            if task.hotspot_group:
                hotspot_groups.setdefault(task.hotspot_group, []).append(task)
            else:
                non_hotspot.append(task)

        slot = 0
        for task in non_hotspot:
            aid = aids[slot % len(aids)]
            slot += 1
            assignments.append(
                WorkAssignment(
                    agent_id=aid,
                    task_id=task.task_id,
                    primary_file=task.primary_file,
                    intent=_intent_for_agent(task, aid),
                )
            )

        for _group, group_tasks in hotspot_groups.items():
            for i, task in enumerate(group_tasks):
                aid = aids[i % len(aids)]
                assignments.append(
                    WorkAssignment(
                        agent_id=aid,
                        task_id=task.task_id,
                        primary_file=task.primary_file,
                        intent=_intent_for_agent(task, aid),
                    )
                )
        return assignments

    raise ValueError(f"Unknown suite: {suite}")


def group_by_agent(assignments: list[WorkAssignment]) -> dict[str, list[WorkAssignment]]:
    grouped: dict[str, list[WorkAssignment]] = {}
    for item in assignments:
        grouped.setdefault(item.agent_id, []).append(item)
    return grouped
