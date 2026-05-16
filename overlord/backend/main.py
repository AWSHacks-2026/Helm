import os
from pathlib import Path
import tempfile

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from agents.scenarios import SCENARIOS, get_scenario_kind
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


@app.get("/")
def root():
    return {
        "service": "Overlord",
        "docs": "/docs",
        "scenarios": "/scenarios",
        "demo_smoke": "/demo/smoke",
    }


@app.get("/scenarios")
def get_scenarios() -> list[str]:
    return list(SCENARIOS.keys())


@app.get("/history")
def get_history(limit: int = 50):
    return kb.get_history(limit=limit)


def _run_guardrail_demo() -> dict:
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


@app.post("/guardrail/check")
def guardrail_check():
    return _run_guardrail_demo()


@app.get("/demo/smoke")
def demo_smoke():
    """Run all three PRD demo paths with mock Bedrock; returns pass/fail checklist."""
    os.environ["OVERLORD_MOCK_BEDROCK"] = "1"
    checks: list[dict] = []

    try:
        scenario = SCENARIOS["merge_conflict"]
        raw = arbitrate(
            scenario["agent_a"],
            scenario["agent_b"],
            conflict_kind="merge",
        )
        ok = raw.get("conflict_type") == "merge_conflict" and "get_user" in raw.get(
            "resolved_code", ""
        )
        checks.append(
            {
                "scenario": "merge_conflict",
                "endpoint": "POST /resolve/merge_conflict",
                "passed": ok,
                "detail": raw.get("conflict_type"),
            }
        )
    except Exception as exc:
        checks.append(
            {
                "scenario": "merge_conflict",
                "endpoint": "POST /resolve/merge_conflict",
                "passed": False,
                "detail": str(exc),
            }
        )

    try:
        scenario = SCENARIOS["intent_conflict"]
        raw = arbitrate(
            scenario["agent_a"],
            scenario["agent_b"],
            conflict_kind="intent",
        )
        ok = raw.get("conflict_type") == "intent_conflict"
        checks.append(
            {
                "scenario": "intent_conflict",
                "endpoint": "POST /resolve/intent_conflict",
                "passed": ok,
                "detail": raw.get("conflict_type"),
            }
        )
    except Exception as exc:
        checks.append(
            {
                "scenario": "intent_conflict",
                "endpoint": "POST /resolve/intent_conflict",
                "passed": False,
                "detail": str(exc),
            }
        )

    try:
        session = Path(tempfile.mkdtemp()) / "smoke-session.json"
        os.environ["OVERLORD_SESSION_PATH"] = str(session)
        result = _run_guardrail_demo()
        ok = (
            result["preflight"]["allowed"] is False
            and result["executed"] is False
            and result["resolution"] is not None
        )
        checks.append(
            {
                "scenario": "guardrail_prevention",
                "endpoint": "POST /guardrail/check",
                "passed": ok,
                "detail": result["preflight"].get("rule"),
            }
        )
    except Exception as exc:
        checks.append(
            {
                "scenario": "guardrail_prevention",
                "endpoint": "POST /guardrail/check",
                "passed": False,
                "detail": str(exc),
            }
        )

    return {
        "all_passed": all(c["passed"] for c in checks),
        "mock_bedrock": True,
        "checks": checks,
    }


@app.post("/resolve/{scenario_name}", response_model=ResolveResponse)
def resolve_conflict(scenario_name: str) -> ResolveResponse:
    if scenario_name not in SCENARIOS:
        raise HTTPException(status_code=404, detail="Scenario not found")

    kind = get_scenario_kind(scenario_name)
    if kind == "guardrail":
        raise HTTPException(
            status_code=400,
            detail="Use POST /guardrail/check for guardrail_prevention scenario",
        )

    scenario = SCENARIOS[scenario_name]
    agent_a = AgentPayload.model_validate(scenario["agent_a"])
    agent_b = AgentPayload.model_validate(scenario["agent_b"])

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
        conflict_kind=kind,
    )
    resolution = ResolutionPayload.model_validate(raw_resolution)

    return ResolveResponse(
        agent_a=agent_a,
        agent_b=agent_b,
        resolution=resolution,
    )
