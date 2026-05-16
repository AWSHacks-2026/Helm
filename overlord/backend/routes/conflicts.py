from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, WebSocket, WebSocketDisconnect

from models import (
    AgentPayload,
    AgentPayloadWithId,
    ConflictApproveRequest,
    ConflictApproveResponse,
    ConflictDetailResponse,
    ConflictStatus,
    ConflictSummary,
    ResolutionPayload,
)

router = APIRouter(tags=["conflicts"])


@router.get("/conflicts/{conflict_id}", response_model=ConflictDetailResponse)
def get_conflict(conflict_id: str, request: Request) -> ConflictDetailResponse:
    store = request.app.state.conflict_store
    record = store.get(conflict_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Conflict not found")

    resolution = ResolutionPayload.model_validate(record.resolution)
    return ConflictDetailResponse(
        conflict_id=record.conflict_id,
        session_id=record.session_id,
        file_path=record.file_path,
        status=record.status,
        agent_a=AgentPayloadWithId(**record.agent_a),
        agent_b=AgentPayloadWithId(**record.agent_b),
        resolution=resolution,
    )


@router.get("/conflicts", response_model=list[ConflictSummary])
def list_conflicts(
    request: Request,
    session_id: str | None = None,
    status: ConflictStatus | None = None,
) -> list[ConflictSummary]:
    store = request.app.state.conflict_store
    return store.list_summaries(session_id=session_id, status=status)


@router.post("/conflicts/{conflict_id}/approve", response_model=ConflictApproveResponse)
def approve_conflict(
    conflict_id: str,
    payload: ConflictApproveRequest,
    request: Request,
    background_tasks: BackgroundTasks,
) -> ConflictApproveResponse:
    store = request.app.state.conflict_store
    record = store.get(conflict_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Conflict not found")

    new_status: ConflictStatus = "approved" if payload.approved else "rejected"
    updated = store.set_status(conflict_id, new_status)

    from bedrock import knowledge_base

    knowledge_base.append_event(
        updated.session_id,
        {
            "event_type": "conflict_approved",
            "payload": {"conflict_id": conflict_id, "status": new_status},
        },
    )

    ws_hub = request.app.state.ws_hub
    background_tasks.add_task(
        ws_hub.broadcast,
        updated.session_id,
        {
            "type": "conflict_approved",
            "conflict": {
                "conflict_id": updated.conflict_id,
                "status": updated.status,
            },
        },
    )

    return ConflictApproveResponse(conflict_id=conflict_id, status=updated.status)


@router.websocket("/ws/conflicts")
async def conflicts_ws(websocket: WebSocket, session_id: str):
    await websocket.accept()
    hub = websocket.app.state.ws_hub

    async def send(data: str) -> None:
        await websocket.send_text(data)

    hub.subscribe(session_id, send)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        hub.unsubscribe(session_id, send)
