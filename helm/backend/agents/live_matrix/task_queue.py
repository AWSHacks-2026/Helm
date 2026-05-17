from __future__ import annotations

from agents.live_matrix.scenarios import WorkAssignment


def build_agent_queues(
    assignments: list[WorkAssignment],
) -> dict[str, list[WorkAssignment]]:
    queues: dict[str, list[WorkAssignment]] = {}
    for item in assignments:
        queues.setdefault(item.agent_id, []).append(item)
    return queues


def all_queues_done(queues: dict[str, list[WorkAssignment]]) -> bool:
    return all(len(q) == 0 for q in queues.values())


def pop_next(queues: dict[str, list[WorkAssignment]], agent_id: str) -> WorkAssignment | None:
    queue = queues.get(agent_id, [])
    if not queue:
        return None
    return queue.pop(0)
