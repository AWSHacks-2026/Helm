from fastapi import APIRouter, BackgroundTasks, Request

from bedrock import knowledge_base
from bedrock.guardrails import check_action
from models import GuardrailCheckRequest, GuardrailCheckResponse

router = APIRouter(tags=["guardrails"])


@router.post("/guardrails/check", response_model=GuardrailCheckResponse)
def guardrails_check(
    payload: GuardrailCheckRequest, request: Request, background_tasks: BackgroundTasks
) -> GuardrailCheckResponse:
    result = check_action(
        session_id=payload.session_id,
        agent_id=payload.agent_id,
        file_path=payload.file_path,
        action=payload.action,
        proposed_code=payload.proposed_code,
        session_store=request.app.state.session_store,
    )
    if not result.allowed:
        event = {
            "event_type": "guardrail_blocked",
            "payload": {**payload.model_dump(), "reason": result.reason},
        }
        knowledge_base.append_event(payload.session_id, event)
        background_tasks.add_task(
            request.app.state.ws_hub.broadcast,
            payload.session_id,
            {"type": "guardrail_blocked", "event": event},
        )
    return result
