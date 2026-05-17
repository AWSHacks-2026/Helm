from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from models import MissionStatus, MissionSummary


@dataclass
class MissionRecord:
    mission_id: str
    session_id: str
    external_id: str | None
    source: str
    title: str
    description: str
    file_path: str
    status: MissionStatus
    assigned_agent_id: str | None
    suggested_task: str | None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class MissionStore:
    def __init__(self) -> None:
        self._by_id: dict[str, MissionRecord] = {}

    def create(
        self,
        *,
        session_id: str,
        title: str,
        description: str = "",
        file_path: str = "",
        external_id: str | None = None,
        source: str = "manual",
        preferred_agent_id: str | None = None,
    ) -> MissionRecord:
        mission_id = str(uuid.uuid4())
        status: MissionStatus = "assigned" if preferred_agent_id else "queued"
        record = MissionRecord(
            mission_id=mission_id,
            session_id=session_id,
            external_id=external_id,
            source=source,
            title=title,
            description=description,
            file_path=file_path,
            status=status,
            assigned_agent_id=preferred_agent_id,
            suggested_task=None,
        )
        self._by_id[mission_id] = record
        return record

    def get(self, mission_id: str) -> MissionRecord | None:
        return self._by_id.get(mission_id)

    def list_summaries(
        self, *, session_id: str | None = None, status: MissionStatus | None = None
    ) -> list[MissionSummary]:
        rows = list(self._by_id.values())
        if session_id:
            rows = [r for r in rows if r.session_id == session_id]
        if status:
            rows = [r for r in rows if r.status == status]
        rows.sort(key=lambda r: r.created_at, reverse=True)
        return [self.to_summary(r) for r in rows]

    def assign(
        self, mission_id: str, agent_id: str, suggested_task: str | None = None
    ) -> MissionRecord:
        record = self._require(mission_id)
        record.assigned_agent_id = agent_id
        record.suggested_task = suggested_task
        record.status = "assigned"
        record.updated_at = datetime.now(timezone.utc).isoformat()
        return record

    def set_status(self, mission_id: str, status: MissionStatus) -> MissionRecord:
        record = self._require(mission_id)
        record.status = status
        record.updated_at = datetime.now(timezone.utc).isoformat()
        return record

    def find_by_external_id(self, external_id: str) -> MissionRecord | None:
        for record in self._by_id.values():
            if record.external_id == external_id:
                return record
        return None

    def list_active_for_session(self, session_id: str) -> list[MissionRecord]:
        active = {"queued", "assigned", "in_progress", "blocked"}
        return [r for r in self._by_id.values() if r.session_id == session_id and r.status in active]

    def to_summary(self, record: MissionRecord) -> MissionSummary:
        return MissionSummary(
            mission_id=record.mission_id,
            session_id=record.session_id,
            external_id=record.external_id,
            source=record.source,
            title=record.title,
            file_path=record.file_path,
            status=record.status,
            assigned_agent_id=record.assigned_agent_id,
            suggested_task=record.suggested_task,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def _require(self, mission_id: str) -> MissionRecord:
        record = self.get(mission_id)
        if not record:
            raise KeyError(mission_id)
        return record
