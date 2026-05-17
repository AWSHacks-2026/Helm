import os
import tempfile
from pathlib import Path

from fastapi import APIRouter

from agents.scenarios import SCENARIOS, get_scenario
from agents.simulator import resolve_intent_conflict
from helm import arbitrate
from routes.guardrail_demo import run_guardrail_demo

router = APIRouter(tags=["demo"])


@router.get("/demo/smoke")
def demo_smoke():
    """Run all three PRD demo paths with mock Bedrock; returns pass/fail checklist."""
    os.environ["HELM_MOCK_BEDROCK"] = "1"
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
                "endpoint": "POST /resolve/demo/merge_conflict",
                "passed": ok,
                "detail": raw.get("conflict_type"),
            }
        )
    except Exception as exc:
        checks.append(
            {
                "scenario": "merge_conflict",
                "endpoint": "POST /resolve/demo/merge_conflict",
                "passed": False,
                "detail": str(exc),
            }
        )

    try:
        scenario = get_scenario("intent_conflict")
        raw = resolve_intent_conflict(
            agent_a=scenario["agent_a"],
            agent_b=scenario["agent_b"],
            history=scenario.get("history", []),
        )
        ok = raw.get("conflict_type") == "intent_conflict"
        checks.append(
            {
                "scenario": "intent_conflict",
                "endpoint": "POST /resolve/demo/intent_conflict",
                "passed": ok,
                "detail": raw.get("conflict_type"),
            }
        )
    except Exception as exc:
        checks.append(
            {
                "scenario": "intent_conflict",
                "endpoint": "POST /resolve/demo/intent_conflict",
                "passed": False,
                "detail": str(exc),
            }
        )

    try:
        session = Path(tempfile.mkdtemp()) / "smoke-session.json"
        os.environ["HELM_SESSION_PATH"] = str(session)
        result = run_guardrail_demo()
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
