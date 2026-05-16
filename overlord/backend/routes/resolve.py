from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from agents.scenarios import SCENARIOS
from models import (
    AgentPayload,
    LiveResolveRequest,
    LiveResolveResponse,
    ResolutionPayload,
    ResolveResponse,
)
from overlord import arbitrate

router = APIRouter(tags=["resolve"])


def _serialize_conflict(record) -> dict:
    return {
        "conflict_id": record.conflict_id,
        "session_id": record.session_id,
        "file_path": record.file_path,
        "status": record.status,
        "conflict_type": record.conflict_type,
        "agent_a_id": record.agent_a_id,
        "agent_b_id": record.agent_b_id,
    }


@router.post("/resolve", response_model=LiveResolveResponse)
def resolve_live(
    payload: LiveResolveRequest,
    request: Request,
    background_tasks: BackgroundTasks,
) -> LiveResolveResponse:
    store = request.app.state.conflict_store
    ws_hub = request.app.state.ws_hub

    agent_a = AgentPayload(intent=payload.agent_a.intent, code=payload.agent_a.code)
    agent_b = AgentPayload(intent=payload.agent_b.intent, code=payload.agent_b.code)

    from bedrock import knowledge_base

    kb_context = knowledge_base.get_context_for_agents(
        [payload.agent_a.agent_id, payload.agent_b.agent_id],
        module_hint=payload.file_path,
    )

    raw = arbitrate(agent_a.model_dump(), agent_b.model_dump(), kb_context=kb_context or None)
    resolution = ResolutionPayload.model_validate(raw)

    record = store.create(
        session_id=payload.session_id,
        file_path=payload.file_path,
        agent_a_id=payload.agent_a.agent_id,
        agent_b_id=payload.agent_b.agent_id,
        conflict_type=resolution.conflict_type,
        agent_a_payload=payload.agent_a.model_dump(),
        agent_b_payload=payload.agent_b.model_dump(),
        resolution_payload=resolution.model_dump(),
    )

    knowledge_base.append_event(
        payload.session_id,
        {
            "event_type": "conflict_resolved",
            "payload": {
                "conflict_id": record.conflict_id,
                "file_path": payload.file_path,
                "resolution": resolution.model_dump(),
            },
        },
    )

    background_tasks.add_task(
        ws_hub.broadcast,
        payload.session_id,
        {"type": "conflict_created", "conflict": _serialize_conflict(record)},
    )

    return LiveResolveResponse(
        conflict_id=record.conflict_id,
        session_id=payload.session_id,
        file_path=payload.file_path,
        status=record.status,
        agent_a=agent_a,
        agent_b=agent_b,
        resolution=resolution,
    )


@router.get("/scenarios")
def get_scenarios() -> list[str]:
    return list(SCENARIOS.keys())


@router.post("/resolve/demo/{scenario_name}", response_model=ResolveResponse)
def resolve_demo_scenario(scenario_name: str, request: Request) -> ResolveResponse:
    if scenario_name not in SCENARIOS:
        raise HTTPException(status_code=404, detail="Scenario not found")

    scenario = SCENARIOS[scenario_name]
    agent_a = AgentPayload.model_validate(scenario["agent_a"])
    agent_b = AgentPayload.model_validate(scenario["agent_b"])

    from bedrock import knowledge_base

    kb_context = None
    try:
        kb_context = knowledge_base.get_context_for_agents(
            ["agent_a", "agent_b"], module_hint="get_user"
        )
    except Exception:
        kb_context = None

    raw_resolution = arbitrate(
        agent_a.model_dump(),
        agent_b.model_dump(),
        kb_context=kb_context or None,
    )
    resolution = ResolutionPayload.model_validate(raw_resolution)

    return ResolveResponse(agent_a=agent_a, agent_b=agent_b, resolution=resolution)
