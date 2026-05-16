from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from agents.scenarios import SCENARIOS, get_scenario
from agents.simulator import resolve_intent_conflict
from bedrock import guardrails, knowledge_base as kb
from bedrock.guardrails import GUARDRAIL_DEMO_SCENARIO, seed_guardrail_demo
from models import AgentPayload, ResolutionPayload, ResolveResponse
from overlord import arbitrate

app = FastAPI(title="Overlord", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/scenarios")
def get_scenarios() -> list[str]:
    return list(SCENARIOS.keys())


@app.get("/history")
def get_history(limit: int = 50):
    return kb.get_history(limit=limit)


@app.post("/guardrail/check")
def guardrail_check():
    seed_guardrail_demo()
    scenario = GUARDRAIL_DEMO_SCENARIO
    result = guardrails.handle_proposed_action(
        scenario["proposed_action"],
        scenario["agent_a"],
        scenario["agent_b"],
    )
    return {
        "agent_a": scenario["agent_a"],
        "agent_b": scenario["agent_b"],
        "proposed_action": scenario["proposed_action"],
        "preflight": result["preflight"],
        "resolution": result["resolution"],
        "executed": result["executed"],
    }


@app.post(
    "/resolve/{scenario_name}",
    response_model=ResolveResponse,
    response_model_exclude_none=True,
)
def resolve_conflict(scenario_name: str) -> ResolveResponse:
    if scenario_name not in SCENARIOS:
        raise HTTPException(status_code=404, detail="Scenario not found")

    scenario = get_scenario(scenario_name)
    agent_a = AgentPayload.model_validate(scenario["agent_a"])
    agent_b = AgentPayload.model_validate(scenario["agent_b"])

    if scenario_name == "intent_conflict":
        raw_resolution = resolve_intent_conflict(
            agent_a=scenario["agent_a"],
            agent_b=scenario["agent_b"],
            history=scenario.get("history", []),
        )
        resolution = ResolutionPayload.model_validate(raw_resolution)
        return ResolveResponse(
            agent_a=agent_a,
            agent_b=agent_b,
            resolution=resolution,
        )

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
        return ResolveResponse(
            agent_a=agent_a,
            agent_b=agent_b,
            resolution=resolution,
        )

    # Optional KB context when bedrock.knowledge_base is available (Person 3).
    kb_context = None
    try:
        from bedrock.knowledge_base import get_context_for_agents

        kb_context = get_context_for_agents(
            ["agent_a", "agent_b"], module_hint="get_user"
        )
    except ImportError:
        pass

    raw_resolution = arbitrate(
        agent_a.model_dump(),
        agent_b.model_dump(),
        kb_context=kb_context,
    )
    resolution = ResolutionPayload.model_validate(raw_resolution)

    return ResolveResponse(
        agent_a=agent_a,
        agent_b=agent_b,
        resolution=resolution,
    )
