from fastapi import APIRouter, BackgroundTasks, Request

from bedrock import knowledge_base
from models import IntentRecordRequest, IntentRecordResponse
from services.intent_alignment import maybe_align_on_declare

router = APIRouter(tags=["intents"])


@router.post("/intents", response_model=IntentRecordResponse)
def record_intent(
    payload: IntentRecordRequest, request: Request, background_tasks: BackgroundTasks
) -> IntentRecordResponse:
    request.app.state.session_store.record_intent(
        session_id=payload.session_id,
        agent_id=payload.agent_id,
        file_path=payload.file_path,
        intent=payload.intent,
    )
    event = {"event_type": "intent_declared", "payload": payload.model_dump()}
    knowledge_base.append_event(payload.session_id, event)
    background_tasks.add_task(
        request.app.state.ws_hub.broadcast,
        payload.session_id,
        {"type": "intent_declared", "event": event},
    )
    align = maybe_align_on_declare(
        session_store=request.app.state.session_store,
        session_id=payload.session_id,
        agent_id=payload.agent_id,
        file_path=payload.file_path,
        intent=payload.intent,
    )
    if align["overlap_detected"] and align["alignment"]:
        knowledge_base.append_event(
            payload.session_id,
            {
                "event_type": "intent_aligned",
                "payload": align["alignment"],
            },
        )
    contention = align["contention"]
    return IntentRecordResponse(
        overlap_detected=align["overlap_detected"],
        alignment=align["alignment"],
        contention=contention,
    )
