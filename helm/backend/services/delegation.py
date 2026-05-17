from __future__ import annotations

from collections import defaultdict
from typing import Any

from helm import detect_duplication, detect_duplication_fleet
from services.thanksgiving_queue import pick_backlog_mission
from store.missions import MissionRecord, MissionStore


def _agent_payload(m: MissionRecord, agent_id: str) -> dict[str, Any]:
    return {
        "intent": f"{m.title}\n{m.description}".strip(),
        "code": m.description,
        "proposed_action": m.title,
    }


def _group_by_file_path(missions: list[MissionRecord]) -> dict[str, list[MissionRecord]]:
    groups: dict[str, list[MissionRecord]] = defaultdict(list)
    for m in missions:
        if m.file_path:
            groups[m.file_path].append(m)
    return groups


def delegate_missions(
    store: MissionStore,
    *,
    session_id: str,
    use_llm_dedup: bool = True,
) -> dict[str, Any]:
    active = store.list_active_for_session(session_id)
    if not active:
        return {
            "session_id": session_id,
            "assignments": [],
            "duplicate_detected": False,
            "reasoning": "no active missions",
        }

    assignments: list[dict[str, Any]] = []
    duplicate_detected = False
    reasoning_parts: list[str] = []

    groups = _group_by_file_path(active)
    for file_path, group in groups.items():
        if len(group) < 2:
            if not group[0].assigned_agent_id:
                store.assign(group[0].mission_id, "agent_a")
                assignments.append(
                    {
                        "mission_id": group[0].mission_id,
                        "assigned_agent_id": "agent_a",
                        "file_path": file_path,
                    }
                )
            continue

        if not use_llm_dedup:
            for i, m in enumerate(group):
                agent_id = f"agent_{chr(ord('a') + i)}"
                store.assign(m.mission_id, agent_id)
                assignments.append({"mission_id": m.mission_id, "assigned_agent_id": agent_id})
            continue

        if len(group) == 2:
            first, second = group[0], group[1]
            agent_a_id = first.assigned_agent_id or "agent_a"
            agent_b_id = second.assigned_agent_id or "agent_b"
            raw = detect_duplication(
                agent_a=_agent_payload(first, agent_a_id),
                agent_b=_agent_payload(second, agent_b_id),
            )
            duplicate_detected = duplicate_detected or bool(raw.get("duplicate_detected"))
            reasoning_parts.append(str(raw.get("reasoning", "")))
            if raw.get("duplicate_detected"):
                continue_id = raw["agent_to_continue"]
                reassign_id = raw["agent_to_reassign"]
                if continue_id == agent_a_id:
                    continue_m, reassign_m = first, second
                else:
                    continue_m, reassign_m = second, first
                store.assign(continue_m.mission_id, continue_id)
                picked = pick_backlog_mission(
                    store, session_id=session_id, exclude_file_paths={file_path}
                )
                if picked:
                    task = f"{picked.title}\n{picked.description}".strip()
                    store.assign(reassign_m.mission_id, reassign_id, task)
                    store.assign(picked.mission_id, reassign_id, task)
                    assignments.append(
                        {
                            "mission_id": continue_m.mission_id,
                            "assigned_agent_id": continue_id,
                            "action": "continue",
                        }
                    )
                    assignments.append(
                        {
                            "mission_id": reassign_m.mission_id,
                            "assigned_agent_id": reassign_id,
                            "action": "reassign",
                            "assignment_source": "thanksgiving_queue",
                            "backlog_mission_id": picked.mission_id,
                            "backlog_external_id": picked.external_id,
                        }
                    )
                else:
                    suggested = raw.get("suggested_new_task")
                    store.assign(reassign_m.mission_id, reassign_id, suggested)
                    assignments.append(
                        {
                            "mission_id": continue_m.mission_id,
                            "assigned_agent_id": continue_id,
                            "action": "continue",
                        }
                    )
                    assignments.append(
                        {
                            "mission_id": reassign_m.mission_id,
                            "assigned_agent_id": reassign_id,
                            "action": "reassign",
                            "assignment_source": "llm_suggested",
                            "suggested_new_task": suggested,
                        }
                    )
            else:
                store.assign(first.mission_id, agent_a_id)
                store.assign(second.mission_id, agent_b_id)
                assignments.append(
                    {"mission_id": first.mission_id, "assigned_agent_id": agent_a_id}
                )
                assignments.append(
                    {"mission_id": second.mission_id, "assigned_agent_id": agent_b_id}
                )
        else:
            agents: dict[str, dict[str, Any]] = {}
            mission_by_agent: dict[str, str] = {}
            for i, m in enumerate(group):
                agent_key = m.assigned_agent_id or f"agent_{chr(ord('a') + i)}"
                agents[agent_key] = {
                    "intent": f"{m.title}\n{m.description}".strip(),
                    "code": m.description,
                    "proposed_action": m.title,
                    "mission_id": m.mission_id,
                }
                mission_by_agent[agent_key] = m.mission_id

            raw = detect_duplication_fleet(agents)
            duplicate_detected = duplicate_detected or bool(raw.get("duplicate_detected"))
            reasoning_parts.append(str(raw.get("reasoning", "")))
            for agent_id in raw.get("continuations") or []:
                mission_id = mission_by_agent[agent_id]
                store.assign(mission_id, agent_id)
                assignments.append(
                    {"mission_id": mission_id, "assigned_agent_id": agent_id, "action": "continue"}
                )
            for item in raw.get("reassignments") or []:
                agent_id = item["agent_id"]
                mission_id = mission_by_agent[agent_id]
                store.assign(mission_id, agent_id, item.get("suggested_new_task"))
                assignments.append(
                    {
                        "mission_id": mission_id,
                        "assigned_agent_id": agent_id,
                        "action": "reassign",
                        "suggested_new_task": item.get("suggested_new_task"),
                    }
                )

    return {
        "session_id": session_id,
        "assignments": assignments,
        "duplicate_detected": duplicate_detected,
        "reasoning": " | ".join(p for p in reasoning_parts if p),
    }
