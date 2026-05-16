"""Hackathon demo route from Person 3 — proactive guardrail scenario."""

from fastapi import APIRouter

from bedrock import guardrails
from bedrock.guardrails import GUARDRAIL_DEMO_SCENARIO, seed_guardrail_demo

router = APIRouter(tags=["guardrails-demo"])


def run_guardrail_demo() -> dict:
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


@router.post("/guardrail/check")
def guardrail_check_demo():
    return run_guardrail_demo()
