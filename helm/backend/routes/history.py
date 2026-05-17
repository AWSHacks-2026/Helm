from fastapi import APIRouter
from pydantic import BaseModel, Field

from bedrock import knowledge_base
from models import HistoryEvent

router = APIRouter(tags=["history"])


class BenchmarkCheckpoint(BaseModel):
    session_id: str
    agent_id: str
    event: str = Field(min_length=1)
    detail: str = ""


class HistoryEventBody(BaseModel):
    session_id: str
    event_type: str = Field(min_length=1)
    payload: dict = Field(default_factory=dict)


@router.get("/history", response_model=list[HistoryEvent])
def get_history(session_id: str) -> list[HistoryEvent]:
    raw_events = knowledge_base.list_history(session_id)
    events: list[HistoryEvent] = []
    for item in raw_events:
        events.append(
            HistoryEvent(
                event_id=item["event_id"],
                session_id=item["session_id"],
                timestamp=item["timestamp"],
                event_type=item["event_type"],
                agent_id=item.get("agent_id"),
                payload=item.get("payload", {}),
            )
        )
    return events


@router.post("/history/event")
def record_history_event(body: HistoryEventBody) -> dict:
    """Record coordination events (replay sync, demos) into session memory."""
    record = knowledge_base.append_event(
        body.session_id,
        {"event_type": body.event_type, "payload": body.payload},
    )
    return {"recorded": True, "event_id": record.get("id", "")}


@router.post("/history/checkpoint")
def record_benchmark_checkpoint(body: BenchmarkCheckpoint) -> dict:
    """Record agent lifecycle events for real-agent benchmark runs."""
    record = knowledge_base.append_event(
        body.session_id,
        {
            "event_type": "benchmark_checkpoint",
            "payload": {
                "agent_id": body.agent_id,
                "event": body.event,
                "detail": body.detail,
            },
        },
    )
    return {"recorded": True, "event_id": record.get("id", "")}
