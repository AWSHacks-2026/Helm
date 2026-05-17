from __future__ import annotations

from store.missions import MissionRecord, MissionStore


def pick_backlog_mission(
    store: MissionStore,
    *,
    session_id: str,
    exclude_file_paths: set[str],
    prefer_unassigned: bool = True,
) -> MissionRecord | None:
    candidates = [
        m
        for m in store.list_active_for_session(session_id)
        if m.file_path
        and m.file_path not in exclude_file_paths
        and m.status in {"queued", "assigned"}
    ]
    if prefer_unassigned:
        unassigned = [m for m in candidates if not m.assigned_agent_id]
        if unassigned:
            candidates = unassigned
    if not candidates:
        return None
    candidates.sort(key=lambda m: m.created_at)
    return candidates[0]
