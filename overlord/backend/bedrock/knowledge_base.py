from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from bedrock import agentcore_memory as mem

_DEFAULT_SESSION = "default"


class RecordType(str, Enum):
    ACTION = "action"
    INTENT = "intent"
    DECISION = "decision"


@dataclass
class KnowledgeRecord:
    id: str
    timestamp: str
    record_type: RecordType
    agent_id: str
    session_id: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["record_type"] = self.record_type.value
        return data


def _record_from_raw(raw: dict[str, Any]) -> KnowledgeRecord:
    rt = raw.get("record_type", "action")
    if isinstance(rt, RecordType):
        record_type = rt
    else:
        record_type = RecordType(rt)
    return KnowledgeRecord(
        id=raw["id"],
        timestamp=raw["timestamp"],
        record_type=record_type,
        agent_id=raw.get("actor_id", raw.get("agent_id", "unknown")),
        session_id=raw.get("session_id", _DEFAULT_SESSION),
        payload=raw.get("payload", {}),
    )


def log_action(
    agent_id: str,
    action_type: str,
    file_path: str,
    description: str,
    metadata: dict[str, Any] | None = None,
    session_id: str = _DEFAULT_SESSION,
) -> KnowledgeRecord:
    raw = mem.log_action(
        session_id,
        agent_id,
        action_type,
        file_path,
        description,
        metadata,
    )
    return _record_from_raw(raw)


def log_intent(
    agent_id: str,
    intent: str,
    session_id: str = _DEFAULT_SESSION,
    file_path: str = "",
) -> KnowledgeRecord:
    raw = mem.log_intent(session_id, agent_id, intent, file_path=file_path)
    return _record_from_raw(raw)


def log_decision(
    reasoning: str,
    affected_agents: list[str],
    decision_id: str | None = None,
    session_id: str = _DEFAULT_SESSION,
) -> KnowledgeRecord:
    raw = mem.log_decision(session_id, reasoning, affected_agents, decision_id)
    return _record_from_raw(raw)


def get_history(
    limit: int = 50,
    record_type: str | None = None,
    agent_id: str | None = None,
    session_id: str = _DEFAULT_SESSION,
) -> list[dict[str, Any]]:
    events = mem.list_events(
        session_id,
        actor_id=agent_id,
        record_type=record_type,
        limit=limit,
    )
    return [
        {
            "id": e["id"],
            "timestamp": e["timestamp"],
            "record_type": e["record_type"],
            "agent_id": e.get("actor_id", e.get("agent_id")),
            "session_id": e["session_id"],
            "payload": e["payload"],
        }
        for e in events
    ]


def get_context_for_agents(
    agent_ids: list[str],
    module_hint: str | None = None,
    session_id: str = _DEFAULT_SESSION,
) -> str:
    query_parts = list(agent_ids)
    if module_hint:
        query_parts.append(module_hint)
    results = retrieve_context(" ".join(query_parts), max_results=5, session_id=session_id)
    return json.dumps(results, indent=2)


def retrieve_context(
    query: str,
    max_results: int = 5,
    session_id: str = _DEFAULT_SESSION,
) -> list[dict[str, Any]]:
    return mem.retrieve_context(session_id, query, top_k=max_results)


def sync_to_s3(session_id: str = _DEFAULT_SESSION) -> str:
    import boto3

    bucket = os.getenv("OVERLORD_S3_BUCKET", "").strip()
    if not bucket:
        raise ValueError("OVERLORD_S3_BUCKET is not configured")

    records = get_history(limit=10_000, session_id=session_id)
    key = f"sessions/{session_id}/{uuid.uuid4()}.json"
    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    client = boto3.client("s3", region_name=region)
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(records, indent=2).encode("utf-8"),
        ContentType="application/json",
    )
    return key


_EVENT_TYPE_BY_RECORD = {
    "intent": "intent_declared",
    "action": "action",
    "decision": "conflict_resolved",
}

_DECISION_EVENT_TYPES = {"conflict_resolved", "conflict_approved"}


def _parse_json_object(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _infer_decision_event_type(payload: dict[str, Any]) -> str | None:
    if "conflict_id" not in payload:
        return None
    if "status" in payload:
        return "conflict_approved"
    if "resolution" in payload:
        return "conflict_resolved"
    return None


def _decision_event_from_payload(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    event_type = "conflict_resolved"
    reasoning_payload = _parse_json_object(payload.get("reasoning"))
    if reasoning_payload is None:
        inferred = _infer_decision_event_type(payload)
        return inferred or event_type, payload

    envelope_event_type = reasoning_payload.get("event_type")
    envelope_payload = reasoning_payload.get("payload")
    if envelope_event_type in _DECISION_EVENT_TYPES and isinstance(envelope_payload, dict):
        return envelope_event_type, envelope_payload

    inferred = _infer_decision_event_type(reasoning_payload)
    return inferred or event_type, reasoning_payload


def append_event(session_id: str, event: dict[str, Any]) -> dict[str, Any]:
    """Bridge agentic workflow events into AgentCore Memory."""
    event_type = event.get("event_type", "")
    payload = event.get("payload", event)

    if event_type == "intent_declared":
        raw = mem.log_intent(
            session_id,
            payload["agent_id"],
            payload["intent"],
            file_path=payload.get("file_path", ""),
        )
        record = _record_from_raw(raw)
    elif event_type == "guardrail_blocked":
        record = log_action(
            agent_id=payload.get("agent_id", "unknown"),
            action_type="guardrail_blocked",
            file_path=payload.get("file_path", ""),
            description=payload.get("reason", "blocked"),
            session_id=session_id,
        )
    elif event_type in {"conflict_resolved", "conflict_approved"}:
        record = log_decision(
            reasoning=json.dumps({"event_type": event_type, "payload": payload}),
            affected_agents=payload.get("affected_agents", []),
            session_id=session_id,
        )
    else:
        record = log_action(
            agent_id=payload.get("agent_id", "unknown"),
            action_type=event_type or "event",
            file_path=payload.get("file_path", ""),
            description=json.dumps(payload),
            session_id=session_id,
        )
    return record.to_dict()


def list_history(session_id: str) -> list[dict[str, Any]]:
    """Session-filtered history for GET /history?session_id=."""
    records = get_history(limit=10_000, session_id=session_id)
    events: list[dict[str, Any]] = []
    for record in sorted(records, key=lambda r: r["timestamp"], reverse=True):
        record_type = record["record_type"]
        payload = record.get("payload", {})
        event_type = _EVENT_TYPE_BY_RECORD.get(record_type, record_type)
        if record_type == "action" and payload.get("action_type") == "guardrail_blocked":
            event_type = "guardrail_blocked"
        if record_type == "decision":
            event_type, payload = _decision_event_from_payload(payload)
        events.append(
            {
                "event_id": record["id"],
                "session_id": record["session_id"],
                "timestamp": record["timestamp"],
                "event_type": event_type,
                "agent_id": record.get("agent_id"),
                "payload": payload,
            }
        )
    return events
