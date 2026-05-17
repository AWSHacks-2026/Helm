from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from bedrock import knowledge_base
from integrations.github.client import GitHubClient
from models import (
    MissionCreateRequest,
    MissionDelegateRequest,
    MissionDelegateResponse,
    MissionStartRequest,
    MissionSummary,
    MissionStatus,
)
from services.delegation import delegate_missions
from services.mission_runner import start_mission

router = APIRouter(prefix="/missions", tags=["missions"])


async def _broadcast_missions(request: Request, session_id: str) -> None:
    hub = request.app.state.ws_hub
    await hub.broadcast(session_id, {"type": "missions_updated"})


@router.post("", response_model=MissionSummary)
async def create_mission(payload: MissionCreateRequest, request: Request) -> MissionSummary:
    store = request.app.state.mission_store
    record = store.create(
        session_id=payload.session_id,
        title=payload.title,
        description=payload.description,
        file_path=payload.file_path,
        external_id=payload.external_id,
        source=payload.source,
        preferred_agent_id=payload.preferred_agent_id,
    )
    knowledge_base.append_event(
        payload.session_id,
        {
            "event_type": "mission_created",
            "payload": {"mission_id": record.mission_id, "title": record.title},
        },
    )
    await _broadcast_missions(request, payload.session_id)
    return store.to_summary(record)


@router.get("", response_model=list[MissionSummary])
def list_missions(
    request: Request,
    session_id: str,
    status: MissionStatus | None = None,
) -> list[MissionSummary]:
    store = request.app.state.mission_store
    return store.list_summaries(session_id=session_id, status=status)


@router.post("/delegate", response_model=MissionDelegateResponse)
async def delegate(payload: MissionDelegateRequest, request: Request) -> MissionDelegateResponse:
    store = request.app.state.mission_store
    result = delegate_missions(
        store, session_id=payload.session_id, use_llm_dedup=payload.use_llm_dedup
    )
    knowledge_base.append_event(
        payload.session_id,
        {"event_type": "mission_delegated", "payload": result},
    )
    client = GitHubClient.from_env()
    if not client.mock and client.token:
        for assignment in result["assignments"]:
            mission = store.get(assignment["mission_id"])
            if mission and mission.external_id and mission.source == "github":
                agent_id = assignment.get("assigned_agent_id", "unassigned")
                action = assignment.get("action", "assign")
                issue_number = client.parse_external_id(mission.external_id)
                client.add_comment(
                    issue_number,
                    f"**Helm** assigned `{agent_id}` ({action})",
                )
    await _broadcast_missions(request, payload.session_id)
    return MissionDelegateResponse(**result)


@router.post("/{mission_id}/start", response_model=MissionSummary)
async def start(
    mission_id: str,
    payload: MissionStartRequest,
    request: Request,
    session_id: str,
) -> MissionSummary:
    store = request.app.state.mission_store
    if not store.get(mission_id):
        raise HTTPException(status_code=404, detail="mission not found")
    try:
        updated = start_mission(
            store,
            mission_id=mission_id,
            session_id=session_id,
            agent_id=payload.agent_id,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    await _broadcast_missions(request, session_id)
    return store.to_summary(updated)
