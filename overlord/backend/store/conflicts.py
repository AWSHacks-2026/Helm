from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from models import ConflictStatus, ConflictSummary


@dataclass
class ConflictRecord:
    conflict_id: str
    session_id: str
    file_path: str
    status: ConflictStatus
    conflict_type: str
    agent_a_id: str
    agent_b_id: str
    agent_a: dict[str, Any]
    agent_b: dict[str, Any]
    resolution: dict[str, Any]
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ConflictStore:
    def __init__(self) -> None:
        self._by_id: dict[str, ConflictRecord] = {}

    def create(
        self,
        *,
        session_id: str,
        file_path: str,
        agent_a_id: str,
        agent_b_id: str,
        conflict_type: str,
        agent_a_payload: dict[str, Any],
        agent_b_payload: dict[str, Any],
        resolution_payload: dict[str, Any],
    ) -> ConflictRecord:
        conflict_id = str(uuid.uuid4())
        record = ConflictRecord(
            conflict_id=conflict_id,
            session_id=session_id,
            file_path=file_path,
            status="pending_approval",
            conflict_type=conflict_type,
            agent_a_id=agent_a_id,
            agent_b_id=agent_b_id,
            agent_a=agent_a_payload,
            agent_b=agent_b_payload,
            resolution=resolution_payload,
        )
        self._by_id[conflict_id] = record
        return record

    def get(self, conflict_id: str) -> ConflictRecord | None:
        return self._by_id.get(conflict_id)

    def set_status(self, conflict_id: str, status: ConflictStatus) -> ConflictRecord:
        record = self._by_id[conflict_id]
        record.status = status
        return record

    def list_summaries(
        self, *, session_id: str | None = None, status: ConflictStatus | None = None
    ) -> list[ConflictSummary]:
        out: list[ConflictSummary] = []
        for record in self._by_id.values():
            if session_id and record.session_id != session_id:
                continue
            if status and record.status != status:
                continue
            out.append(
                ConflictSummary(
                    conflict_id=record.conflict_id,
                    session_id=record.session_id,
                    file_path=record.file_path,
                    status=record.status,
                    conflict_type=record.conflict_type,
                    created_at=record.created_at,
                    agent_a_id=record.agent_a_id,
                    agent_b_id=record.agent_b_id,
                )
            )
        return sorted(out, key=lambda item: item.created_at, reverse=True)
