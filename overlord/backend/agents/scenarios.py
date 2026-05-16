from copy import deepcopy
from typing import Any

from agents.merge_scenarios import MERGE_SCENARIO_META, MERGE_SCENARIOS
from bedrock.guardrails import GUARDRAIL_DEMO_SCENARIO

SCENARIO_META: dict[str, dict[str, str]] = {
    **MERGE_SCENARIO_META,
    "intent_conflict": {
        "kind": "intent",
        "title": "Act 2 — Performance vs minimal dependencies",
        "description": "Contradictory goals before code diverges.",
    },
    "dependency_conflict": {
        "kind": "dependency",
        "title": "Redis vs in-memory cache",
        "description": "Conflicting dependency changes on requirements.txt.",
    },
    "guardrail_prevention": {
        "kind": "guardrail",
        "title": "Act 3 — Block delete of peer's cache utility",
        "description": "Use POST /guardrail/check (not /resolve) for full flow.",
    },
}

SCENARIOS: dict[str, dict[str, Any]] = {
    **MERGE_SCENARIOS,
    "intent_conflict": {
        "title": "Performance vs. Minimalism",
        "agent_a": {
            "intent": (
                "I am optimizing this module for maximum performance, even if it means "
                "adding specialized caching and parsing dependencies."
            ),
            "code": (
                "# Agent A has not written code yet. It plans to add orjson and cache "
                "hot-path parsed payloads."
            ),
            "proposed_action": (
                "Add orjson plus an LRU cache around payload normalization for maximum "
                "request throughput."
            ),
        },
        "agent_b": {
            "intent": (
                "I am refactoring this module to minimize external dependencies and keep "
                "the deployment artifact small."
            ),
            "code": (
                "# Agent B has not written code yet. It plans to replace optional parsing "
                "libraries with standard library json."
            ),
            "proposed_action": (
                "Remove optional parser dependencies and use standard library json with "
                "clear validation functions."
            ),
        },
        "history": [
            {
                "agent": "agent_a",
                "decision": "Prioritized low-latency request handling in the API layer.",
            },
            {
                "agent": "agent_b",
                "decision": "Reduced image size by removing unused transitive dependencies.",
            },
        ],
    },
    "dependency_conflict": {
        "title": "Redis vs. In-Memory Cache",
        "agent_a": {
            "intent": "I am adding Redis for caching to improve response times.",
            "code": "# requirements.txt addition: redis",
            "proposed_action": "Add redis and configure a shared cache client.",
        },
        "agent_b": {
            "intent": "I am removing unnecessary dependencies to reduce image size.",
            "code": "# requirements.txt: remove redis and keep an in-memory dictionary cache",
            "proposed_action": "Remove redis and keep caching inside the process.",
        },
        "history": [],
    },
    "guardrail_prevention": {
        "agent_a": GUARDRAIL_DEMO_SCENARIO["agent_a"],
        "agent_b": GUARDRAIL_DEMO_SCENARIO["agent_b"],
    },
}


def get_scenario_kind(name: str) -> str:
    return SCENARIO_META[name]["kind"]


def get_scenario_names() -> list[str]:
    return list(SCENARIOS.keys())


def get_scenario(name: str) -> dict[str, Any]:
    return deepcopy(SCENARIOS[name])
