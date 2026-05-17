from fastapi import APIRouter

from bedrock import knowledge_base
from services.gratitude_ledger import build_gratitude_ledger

router = APIRouter(tags=["gratitude"])


@router.get("/gratitude")
def get_gratitude(session_id: str) -> dict:
    events = knowledge_base.list_history(session_id)
    ledger = build_gratitude_ledger(events)
    return ledger.__dict__
