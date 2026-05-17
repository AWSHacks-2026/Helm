from __future__ import annotations

from dataclasses import dataclass, field
from typing import DefaultDict
from collections import defaultdict


@dataclass
class IntentRecord:
    session_id: str
    agent_id: str
    file_path: str
    intent: str


class SessionStore:
    def __init__(self) -> None:
        self._intents: DefaultDict[str, list[IntentRecord]] = defaultdict(list)

    def record_intent(
        self, *, session_id: str, agent_id: str, file_path: str, intent: str
    ) -> IntentRecord:
        record = IntentRecord(
            session_id=session_id,
            agent_id=agent_id,
            file_path=file_path,
            intent=intent,
        )
        self._intents[session_id].append(record)
        return record

    def agents_on_file(
        self, session_id: str, file_path: str, exclude: str | None = None
    ) -> list[str]:
        agents: list[str] = []
        for record in self._intents.get(session_id, []):
            if record.file_path != file_path:
                continue
            if exclude and record.agent_id == exclude:
                continue
            if record.agent_id not in agents:
                agents.append(record.agent_id)
        return agents

    def intents_on_file(
        self, session_id: str, file_path: str, exclude: str | None = None
    ) -> list[dict[str, str]]:
        """Latest intent per agent on file (for handoff / alignment)."""
        latest: dict[str, str] = {}
        for record in self._intents.get(session_id, []):
            if record.file_path != file_path:
                continue
            if exclude and record.agent_id == exclude:
                continue
            latest[record.agent_id] = record.intent
        return [{"agent_id": aid, "intent": intent} for aid, intent in latest.items()]

    def latest_intent_for_agent(
        self, session_id: str, agent_id: str, file_path: str
    ) -> str | None:
        intent: str | None = None
        for record in self._intents.get(session_id, []):
            if record.file_path == file_path and record.agent_id == agent_id:
                intent = record.intent
        return intent
