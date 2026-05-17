from __future__ import annotations

from bedrock import knowledge_base
from session.agent_identity import resolve_agent_id
from store.missions import MissionRecord, MissionStore


def start_mission(
    store: MissionStore,
    *,
    mission_id: str,
    session_id: str,
    agent_id: str | None = None,
) -> MissionRecord:
    record = store.get(mission_id)
    if not record:
        raise KeyError(mission_id)
    worker = agent_id or resolve_agent_id()
    if record.assigned_agent_id and record.assigned_agent_id != worker:
        store.set_status(mission_id, "blocked")
        raise PermissionError(
            f"mission assigned to {record.assigned_agent_id}, not {worker}"
        )
    if not record.assigned_agent_id:
        store.assign(mission_id, worker)
    intent_text = record.suggested_task or record.title
    knowledge_base.log_intent(
        worker,
        intent_text,
        session_id=session_id,
        file_path=record.file_path,
    )
    knowledge_base.append_event(
        session_id,
        {
            "event_type": "mission_started",
            "payload": {
                "mission_id": mission_id,
                "agent_id": worker,
                "file_path": record.file_path,
                "external_id": record.external_id,
                "intent": intent_text,
            },
        },
    )
    return store.set_status(mission_id, "in_progress")
