import os
import tempfile
from pathlib import Path

from fastapi import APIRouter

from agents.scenarios import SCENARIOS
from overlord import arbitrate
from routes.guardrail_demo import run_guardrail_demo

router = APIRouter(tags=["demo"])


@router.get("/demo/smoke")
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
        os.environ["OVERLORD_SESSION_PATH"] = str(session)
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
