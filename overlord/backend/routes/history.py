from fastapi import APIRouter

from bedrock import knowledge_base
from models import HistoryEvent

router = APIRouter(tags=["history"])


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
                payload=item.get("payload", {}),
            )
        )
    return events
