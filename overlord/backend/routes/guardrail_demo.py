"""Hackathon demo route — proactive guardrail scenario."""

import os
import tempfile
from pathlib import Path

from fastapi import APIRouter

from bedrock import guardrails
from bedrock.guardrails import GUARDRAIL_DEMO_SCENARIO, seed_guardrail_demo

router = APIRouter(tags=["guardrails-demo"])

_DEMO_SESSION = "guardrail-demo"


def run_guardrail_demo(session_id: str = _DEMO_SESSION) -> dict:
    if session_id == _DEMO_SESSION:
        session_path = Path(tempfile.mkdtemp()) / f"{session_id}.json"
        os.environ["OVERLORD_SESSION_PATH"] = str(session_path)

    seed_guardrail_demo(session_id=session_id)
    scenario = GUARDRAIL_DEMO_SCENARIO
    result = guardrails.handle_proposed_action(
        scenario["proposed_action"],
        scenario["agent_a"],
        scenario["agent_b"],
        session_id=session_id,
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
