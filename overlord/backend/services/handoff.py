from __future__ import annotations

from models import GratitudeHandoff
from services.thanksgiving_queue import pick_backlog_mission
from store.missions import MissionStore
from store.sessions import SessionStore


def build_gratitude_handoff(
    *,
    session_id: str,
    blocked_agent_id: str,
    file_path: str,
    session_store: SessionStore,
    mission_store: MissionStore | None = None,
    owners: list[dict[str, str]] | None = None,
) -> GratitudeHandoff:
    if owners is None:
        owners = session_store.intents_on_file(session_id, file_path, exclude=blocked_agent_id)
    owner_agent_id = owners[0]["agent_id"] if owners else "unknown"
    owner_intent = owners[0]["intent"] if owners else "active work on this file"

    suggested_file_path = None
    suggested_mission_id = None
    suggested_task = None
    if mission_store is not None:
        picked = pick_backlog_mission(
            mission_store,
            session_id=session_id,
            exclude_file_paths={file_path},
        )
        if picked is not None:
            suggested_mission_id = picked.mission_id
            suggested_file_path = picked.file_path
            suggested_task = f"{picked.title}\n{picked.description}".strip()

    message = (
        f"Thanks for coordinating — {owner_agent_id} is carrying `{file_path}` "
        f"({owner_intent})."
    )
    if suggested_file_path:
        message += f" You can help on `{suggested_file_path}` instead."

    return GratitudeHandoff(
        owner_agent_id=owner_agent_id,
        owner_intent=owner_intent,
        message=message,
        suggested_file_path=suggested_file_path,
        suggested_mission_id=suggested_mission_id,
        suggested_task=suggested_task,
    )
