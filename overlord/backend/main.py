from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from agents.scenarios import SCENARIOS
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


@app.post("/resolve/{scenario_name}", response_model=ResolveResponse)
def resolve_conflict(scenario_name: str) -> ResolveResponse:
    if scenario_name not in SCENARIOS:
        raise HTTPException(status_code=404, detail="Scenario not found")

    scenario = SCENARIOS[scenario_name]
    agent_a = AgentPayload.model_validate(scenario["agent_a"])
    agent_b = AgentPayload.model_validate(scenario["agent_b"])

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
