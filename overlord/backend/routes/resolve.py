from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from agents.scenarios import SCENARIOS, get_scenario, get_scenario_kind, get_scenario_names
from agents.simulator import resolve_intent_conflict
from models import (
    AgentPayload,
    LiveResolveRequest,
    LiveResolveResponse,
    ResolutionPayload,
    ResolveResponse,
)
from overlord import arbitrate, detect_duplication

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
        session_id=payload.session_id,
    )

    arbitrate_kwargs = {
        "kb_context": kb_context or None,
        "session_id": payload.session_id,
    }
    if payload.conflict_kind is not None:
        arbitrate_kwargs["conflict_kind"] = payload.conflict_kind

    raw = arbitrate(
        agent_a.model_dump(),
        agent_b.model_dump(),
        **arbitrate_kwargs,
    )
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
    return get_scenario_names()


@router.post(
    "/resolve/{scenario_name}",
    response_model=ResolveResponse,
    response_model_exclude_none=True,
)
@router.post(
    "/resolve/demo/{scenario_name}",
    response_model=ResolveResponse,
    response_model_exclude_none=True,
)
def resolve_demo_scenario(scenario_name: str, request: Request) -> ResolveResponse:
    if scenario_name not in SCENARIOS:
        raise HTTPException(status_code=404, detail="Scenario not found")

    kind = get_scenario_kind(scenario_name)
    if kind == "guardrail":
        raise HTTPException(
            status_code=400,
            detail="Use POST /guardrail/check for guardrail_prevention scenario",
        )

    scenario = get_scenario(scenario_name)
    agent_a = AgentPayload.model_validate(scenario["agent_a"])
    agent_b = AgentPayload.model_validate(scenario["agent_b"])

    if scenario_name == "duplicate_work":
        raw_resolution = detect_duplication(
            agent_a=scenario["agent_a"],
            agent_b=scenario["agent_b"],
        )
        resolution = ResolutionPayload.model_validate(raw_resolution)
        return ResolveResponse(agent_a=agent_a, agent_b=agent_b, resolution=resolution)

    if scenario_name == "intent_conflict":
        raw_resolution = resolve_intent_conflict(
            agent_a=scenario["agent_a"],
            agent_b=scenario["agent_b"],
            history=scenario.get("history", []),
        )
        resolution = ResolutionPayload.model_validate(raw_resolution)
        return ResolveResponse(agent_a=agent_a, agent_b=agent_b, resolution=resolution)

    if scenario_name == "dependency_conflict":
        raw_resolution = {
            "conflict_type": "dependency_conflict",
            "reasoning": (
                "The dependency scenario is part of the shared demo catalog; "
                "full dependency arbitration belongs to another feature owner "
                "or a future resolver."
            ),
            "resolved_code": (
                "Directive: avoid adding Redis until benchmark evidence "
                "justifies the dependency on the demo path."
            ),
            "tokens_saved_estimate": "0 tokens saved (0%)",
        }
        resolution = ResolutionPayload.model_validate(raw_resolution)
        return ResolveResponse(agent_a=agent_a, agent_b=agent_b, resolution=resolution)

    from bedrock import knowledge_base

    kb_context = None
    module_hint = scenario.get("file_path", "get_user")
    try:
        kb_context = knowledge_base.get_context_for_agents(
            ["agent_a", "agent_b"],
            module_hint=module_hint,
        )
    except Exception:
        kb_context = None

    raw_resolution = arbitrate(
        agent_a.model_dump(),
        agent_b.model_dump(),
        kb_context=kb_context or None,
        conflict_kind=kind,
        session_id=f"demo-{scenario_name}",
    )
    resolution = ResolutionPayload.model_validate(raw_resolution)

    return ResolveResponse(agent_a=agent_a, agent_b=agent_b, resolution=resolution)
