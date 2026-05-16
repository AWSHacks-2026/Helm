from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _use_local() -> bool:
    return os.getenv("OVERLORD_USE_LOCAL_MEMORY", "true").lower() == "true"


def _local_path() -> Path:
    return Path(os.getenv("OVERLORD_SESSION_PATH", ".overlord/session.json"))


def _namespace(session_id: str, actor_id: str) -> str:
    return f"overlord/sessions/{session_id}/agents/{actor_id}/"


def _read_local() -> list[dict[str, Any]]:
    path = _local_path()
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _append_local(record: dict[str, Any]) -> dict[str, Any]:
    path = _local_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    records = _read_local()
    records.append(record)
    path.write_text(json.dumps(records, indent=2), encoding="utf-8")
    return record


def _memory_id() -> str:
    return os.getenv("AGENTCORE_MEMORY_ID", "").strip()


def log_action(
    session_id: str,
    actor_id: str,
    action_type: str,
    file_path: str,
    description: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "actor_id": actor_id,
        "record_type": "action",
        "payload": {
            "action_type": action_type,
            "file_path": file_path,
            "description": description,
            "metadata": metadata or {},
        },
    }
    if _use_local() or not _memory_id():
        return _append_local(record)

    from bedrock_agentcore.memory import MemoryClient

    client = MemoryClient()
    client.create_event(
        memory_id=_memory_id(),
        actor_id=actor_id,
        session_id=session_id,
        messages=[(json.dumps(record["payload"]), "TOOL")],
        metadata={
            "record_type": {"stringValue": "action"},
            "file_path": {"stringValue": file_path},
            "action_type": {"stringValue": action_type},
        },
    )
    return record


def log_intent(
    session_id: str,
    actor_id: str,
    intent: str,
    file_path: str = "",
) -> dict[str, Any]:
    record = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "actor_id": actor_id,
        "record_type": "intent",
        "payload": {"intent": intent, "file_path": file_path},
    }
    if _use_local() or not _memory_id():
        return _append_local(record)

    from bedrock_agentcore.memory import MemoryClient

    client = MemoryClient()
    client.create_event(
        memory_id=_memory_id(),
        actor_id=actor_id,
        session_id=session_id,
        messages=[(intent, "USER")],
        metadata={"record_type": {"stringValue": "intent"}},
    )
    return record


def log_decision(
    session_id: str,
    reasoning: str,
    affected_agents: list[str],
    decision_id: str | None = None,
) -> dict[str, Any]:
    record = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "actor_id": "overlord",
        "record_type": "decision",
        "payload": {
            "decision_id": decision_id or str(uuid.uuid4()),
            "reasoning": reasoning,
            "affected_agents": affected_agents,
        },
    }
    if _use_local() or not _memory_id():
        return _append_local(record)

    from bedrock_agentcore.memory import MemoryClient

    client = MemoryClient()
    client.create_event(
        memory_id=_memory_id(),
        actor_id="overlord",
        session_id=session_id,
        messages=[(reasoning, "ASSISTANT")],
        metadata={"record_type": {"stringValue": "decision"}},
    )
    return record


def list_events(
    session_id: str,
    *,
    actor_id: str | None = None,
    record_type: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    if _use_local() or not _memory_id():
        records = [r for r in _read_local() if r.get("session_id") == session_id]
        if actor_id:
            records = [r for r in records if r.get("actor_id") == actor_id]
        if record_type:
            records = [r for r in records if r.get("record_type") == record_type]
        return records[-limit:]

    from bedrock_agentcore.memory import MemoryClient

    client = MemoryClient()
    actors = [actor_id] if actor_id else _distinct_actors(session_id)
    out: list[dict[str, Any]] = []
    for aid in actors:
        resp = client.list_events(
            memory_id=_memory_id(),
            actor_id=aid,
            session_id=session_id,
            max_results=min(limit, 100),
        )
        for ev in resp.get("events", []):
            out.append(_event_to_record(session_id, aid, ev))
    out.sort(key=lambda r: r["timestamp"])
    if record_type:
        out = [r for r in out if r.get("record_type") == record_type]
    return out[-limit:]


def retrieve_context(session_id: str, query: str, top_k: int = 5) -> list[dict[str, Any]]:
    if _use_local() or not _memory_id():
        return _retrieve_local(session_id, query, top_k)

    from bedrock_agentcore.memory import MemoryClient

    client = MemoryClient()
    memories: list[dict[str, Any]] = []
    for aid in _distinct_actors(session_id):
        ns = _namespace(session_id, aid)
        memories.extend(
            client.retrieve_memories(
                memory_id=_memory_id(),
                namespace=ns,
                query=query,
                top_k=top_k,
            )
        )
    return memories[:top_k]


def _retrieve_local(session_id: str, query: str, top_k: int) -> list[dict[str, Any]]:
    tokens = {t.lower() for t in query.split() if len(t) > 2}
    scored: list[tuple[int, dict[str, Any]]] = []
    for record in _read_local():
        if record.get("session_id") != session_id:
            continue
        blob = json.dumps(record).lower()
        score = sum(1 for t in tokens if t in blob)
        if score:
            scored.append((score, record))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored[:top_k]]


def _distinct_actors(session_id: str) -> list[str]:
    if _use_local() or not _memory_id():
        actors = {
            r.get("actor_id")
            for r in _read_local()
            if r.get("session_id") == session_id and r.get("actor_id")
        }
        return sorted(actors) or ["agent_a", "agent_b", "overlord"]
    return ["agent_a", "agent_b", "overlord"]


def _event_to_record(session_id: str, actor_id: str, event: dict[str, Any]) -> dict[str, Any]:
    meta = event.get("metadata") or {}
    record_type = (meta.get("record_type") or {}).get("stringValue", "action")
    payload_raw = event.get("payload")
    if isinstance(payload_raw, str):
        try:
            payload = json.loads(payload_raw)
        except json.JSONDecodeError:
            payload = {"text": payload_raw}
    else:
        payload = payload_raw if isinstance(payload_raw, dict) else {}
    return {
        "id": event.get("eventId", ""),
        "timestamp": event.get("eventTimestamp", ""),
        "session_id": session_id,
        "actor_id": actor_id,
        "record_type": record_type,
        "payload": payload,
    }
