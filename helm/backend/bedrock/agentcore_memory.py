from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _use_local() -> bool:
    return os.getenv("HELM_USE_LOCAL_MEMORY", "true").lower() == "true"


def _local_path() -> Path:
    return Path(os.getenv("HELM_SESSION_PATH", ".helm/session.json"))


def _namespace(session_id: str, actor_id: str) -> str:
    return f"helm/sessions/{session_id}/agents/{actor_id}/"


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

    try:
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
    except Exception:
        return _append_local(record)


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

    try:
        from bedrock_agentcore.memory import MemoryClient

        client = MemoryClient()
        client.create_event(
            memory_id=_memory_id(),
            actor_id=actor_id,
            session_id=session_id,
            messages=[(intent, "USER")],
            metadata={
                "record_type": {"stringValue": "intent"},
                "file_path": {"stringValue": file_path},
            },
        )
        return record
    except Exception:
        return _append_local(record)


def agents_on_file(
    session_id: str,
    file_path: str,
    *,
    exclude: str | None = None,
) -> list[str]:
    agents: list[str] = []
    for record in list_events(session_id, record_type="intent", limit=200):
        payload = record.get("payload", {})
        if payload.get("file_path") != file_path:
            continue
        aid = record.get("actor_id", "")
        if exclude and aid == exclude:
            continue
        if aid and aid not in agents:
            agents.append(aid)
    return agents


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
        "actor_id": "helm",
        "record_type": "decision",
        "payload": {
            "decision_id": decision_id or str(uuid.uuid4()),
            "reasoning": reasoning,
            "affected_agents": affected_agents,
        },
    }
    if _use_local() or not _memory_id():
        return _append_local(record)

    try:
        from bedrock_agentcore.memory import MemoryClient

        client = MemoryClient()
        client.create_event(
            memory_id=_memory_id(),
            actor_id="helm",
            session_id=session_id,
            messages=[(reasoning, "ASSISTANT")],
            metadata={"record_type": {"stringValue": "decision"}},
        )
        return record
    except Exception:
        return _append_local(record)


def _list_events_local(
    session_id: str,
    *,
    actor_id: str | None = None,
    record_type: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    records = [r for r in _read_local() if r.get("session_id") == session_id]
    if actor_id:
        records = [r for r in records if r.get("actor_id") == actor_id]
    if record_type:
        records = [r for r in records if r.get("record_type") == record_type]
    return records[-limit:]


def list_events(
    session_id: str,
    *,
    actor_id: str | None = None,
    record_type: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    if _use_local() or not _memory_id():
        return _list_events_local(
            session_id,
            actor_id=actor_id,
            record_type=record_type,
            limit=limit,
        )

    try:
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
            events = resp if isinstance(resp, list) else resp.get("events", [])
            for ev in events:
                out.append(_event_to_record(session_id, aid, ev))
        out.sort(key=lambda r: r["timestamp"])
        if record_type:
            out = [r for r in out if r.get("record_type") == record_type]
        return out[-limit:]
    except Exception:
        return _list_events_local(
            session_id,
            actor_id=actor_id,
            record_type=record_type,
            limit=limit,
        )


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
        return sorted(actors) or ["agent_a", "agent_b", "helm"]
    return ["agent_a", "agent_b", "helm"]


def _parse_event_payload(payload_raw: Any) -> dict[str, Any]:
    if isinstance(payload_raw, str):
        try:
            parsed = json.loads(payload_raw)
            return parsed if isinstance(parsed, dict) else {"text": payload_raw}
        except json.JSONDecodeError:
            return {"text": payload_raw}
    if isinstance(payload_raw, dict):
        return payload_raw
    if isinstance(payload_raw, list):
        texts: list[str] = []
        for item in payload_raw:
            if not isinstance(item, dict):
                continue
            block = item.get("conversational") or item.get("tool") or item
            content = block.get("content") if isinstance(block, dict) else None
            if isinstance(content, dict) and content.get("text"):
                texts.append(str(content["text"]))
            elif isinstance(content, str):
                texts.append(content)
        if not texts:
            return {}
        blob = texts[0] if len(texts) == 1 else "\n".join(texts)
        try:
            parsed = json.loads(blob)
            return parsed if isinstance(parsed, dict) else {"text": blob}
        except json.JSONDecodeError:
            return {"intent": blob, "text": blob}
    return {}


def _metadata_string(meta: dict[str, Any], key: str, default: str = "") -> str:
    value = meta.get(key, default)
    if isinstance(value, dict):
        return str(value.get("stringValue", default))
    return str(value) if value is not None else default


def _event_to_record(session_id: str, actor_id: str, event: dict[str, Any]) -> dict[str, Any]:
    meta = event.get("metadata") or {}
    record_type = _metadata_string(meta, "record_type", "action")
    payload = _parse_event_payload(event.get("payload"))
    ts = event.get("eventTimestamp", "")
    if hasattr(ts, "isoformat"):
        ts = ts.isoformat()
    return {
        "id": event.get("eventId", event.get("event_id", "")),
        "timestamp": ts,
        "session_id": session_id,
        "actor_id": event.get("actorId", actor_id),
        "record_type": record_type,
        "payload": payload,
    }
