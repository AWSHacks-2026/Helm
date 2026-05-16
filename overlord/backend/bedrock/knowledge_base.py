from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


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


def _session_path() -> Path:
    return Path(os.getenv("OVERLORD_SESSION_PATH", ".overlord/session.json"))


def _use_local_kb() -> bool:
    return os.getenv("OVERLORD_USE_LOCAL_KB", "true").lower() == "true"


def _read_all() -> list[dict[str, Any]]:
    path = _session_path()
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _append(record: KnowledgeRecord) -> KnowledgeRecord:
    path = _session_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    records = _read_all()
    records.append(record.to_dict())
    path.write_text(json.dumps(records, indent=2), encoding="utf-8")
    return record


def _make_record(
    record_type: RecordType,
    agent_id: str,
    payload: dict[str, Any],
    session_id: str = "default",
) -> KnowledgeRecord:
    return KnowledgeRecord(
        id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc).isoformat(),
        record_type=record_type,
        agent_id=agent_id,
        session_id=session_id,
        payload=payload,
    )


def log_action(
    agent_id: str,
    action_type: str,
    file_path: str,
    description: str,
    metadata: dict[str, Any] | None = None,
    session_id: str = "default",
) -> KnowledgeRecord:
    payload = {
        "action_type": action_type,
        "file_path": file_path,
        "description": description,
        "metadata": metadata or {},
    }
    record = _make_record(RecordType.ACTION, agent_id, payload, session_id)
    return _append(record)


def log_intent(agent_id: str, intent: str, session_id: str = "default") -> KnowledgeRecord:
    record = _make_record(
        RecordType.INTENT,
        agent_id,
        {"intent": intent},
        session_id,
    )
    return _append(record)


def log_decision(
    reasoning: str,
    affected_agents: list[str],
    decision_id: str | None = None,
    session_id: str = "default",
) -> KnowledgeRecord:
    payload = {
        "decision_id": decision_id or str(uuid.uuid4()),
        "reasoning": reasoning,
        "affected_agents": affected_agents,
    }
    record = _make_record(RecordType.DECISION, "overlord", payload, session_id)
    return _append(record)


def get_history(
    limit: int = 50,
    record_type: str | None = None,
    agent_id: str | None = None,
) -> list[dict[str, Any]]:
    records = _read_all()
    if record_type:
        records = [r for r in records if r["record_type"] == record_type]
    if agent_id:
        records = [r for r in records if r["agent_id"] == agent_id]
    return records[-limit:]


def get_context_for_agents(
    agent_ids: list[str],
    module_hint: str | None = None,
) -> str:
    query_parts = list(agent_ids)
    if module_hint:
        query_parts.append(module_hint)
    results = retrieve_context(" ".join(query_parts), max_results=5)
    return json.dumps(results, indent=2)


def retrieve_context(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    kb_id = os.getenv("BEDROCK_KB_ID", "").strip()
    if kb_id and not _use_local_kb():
        return _retrieve_from_bedrock(query, max_results, kb_id)
    return _retrieve_local(query, max_results)


def _retrieve_local(query: str, max_results: int) -> list[dict[str, Any]]:
    tokens = {t.lower() for t in query.split() if len(t) > 2}
    scored: list[tuple[int, dict[str, Any]]] = []
    for record in _read_all():
        blob = json.dumps(record).lower()
        score = sum(1 for t in tokens if t in blob)
        if score:
            scored.append((score, record))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored[:max_results]]


def _retrieve_from_bedrock(query: str, max_results: int, kb_id: str) -> list[dict[str, Any]]:
    from bedrock.client import get_bedrock_agent_client

    client = get_bedrock_agent_client()
    response = client.retrieve(
        knowledgeBaseId=kb_id,
        retrievalQuery={"text": query},
        retrievalConfiguration={
            "vectorSearchConfiguration": {"numberOfResults": max_results}
        },
    )
    results = []
    for item in response.get("retrievalResults", []):
        results.append(
            {
                "score": item.get("score"),
                "content": item.get("content", {}).get("text", ""),
                "metadata": item.get("metadata", {}),
            }
        )
    return results


def sync_to_s3(session_id: str = "default") -> str:
    import boto3

    bucket = os.getenv("OVERLORD_S3_BUCKET", "").strip()
    if not bucket:
        raise ValueError("OVERLORD_S3_BUCKET is not configured")

    records = _read_all()
    key = f"sessions/{session_id}/{uuid.uuid4()}.json"
    client = boto3.client("s3", region_name=os.getenv("AWS_REGION", "us-east-1"))
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(records, indent=2).encode("utf-8"),
        ContentType="application/json",
    )
    return key
