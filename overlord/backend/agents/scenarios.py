from copy import deepcopy
from typing import Any

from bedrock.guardrails import GUARDRAIL_DEMO_SCENARIO

SCENARIOS: dict[str, dict[str, Any]] = {
    "merge_conflict": {
        "agent_a": {
            "intent": "I am optimizing this function for speed using caching",
            "code": """
def get_user(user_id):
    if user_id in cache:
        return cache[user_id]
    result = db.query(user_id)
    cache[user_id] = result
    return result
""".strip(),
        },
        "agent_b": {
            "intent": "I am refactoring this function for readability and adding type hints",
            "code": """
def get_user(user_id: str) -> User:
    return db.query(user_id)
""".strip(),
        },
    },
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
    "duplicate_work": {
        "title": "Duplicate User Authentication Work",
        "agent_a": {
            "intent": (
                "I am implementing JWT-based user authentication for the API login flow."
            ),
            "code": (
                "# Agent A plans to add login endpoints, password verification, "
                "and JWT token creation."
            ),
            "proposed_action": (
                "Build API authentication endpoints for login and token issuance."
            ),
        },
        "agent_b": {
            "intent": (
                "I am building user sign-in and session validation for the same API."
            ),
            "code": (
                "# Agent B plans to add sign-in handlers, session validation, "
                "and authenticated request checks."
            ),
            "proposed_action": (
                "Build sign-in and session validation for authenticated API access."
            ),
        },
        "history": [
            {
                "agent": "agent_a",
                "decision": "Claimed ownership of API login and token creation.",
            },
            {
                "agent": "agent_b",
                "decision": "Started a parallel sign-in and session validation task.",
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


def get_scenario_names() -> list[str]:
    return list(SCENARIOS.keys())


def get_scenario(name: str) -> dict[str, Any]:
    return deepcopy(SCENARIOS[name])
