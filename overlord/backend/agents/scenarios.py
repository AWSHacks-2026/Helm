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
    "duplicate_work": {
        "kind": "duplicate_work",
        "title": "Duplicate user authentication work",
        "description": "Overlapping authentication intents before agents duplicate effort.",
    },
    "duplicate_work_fleet": {
        "kind": "duplicate_work",
        "title": "Six-agent commerce platform duplication",
        "description": "Multiple agents overlap on auth and catalog; one Overlord call coordinates all.",
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
    "duplicate_work_fleet": {
        "title": "Commerce Platform — Six Agent Duplication",
        "file_path": "app/auth/handlers.py",
        "file_paths": {
            "agent_a": "app/auth/handlers.py",
            "agent_b": "app/auth/handlers.py",
            "agent_c": "app/auth/handlers.py",
            "agent_d": "app/catalog/products.py",
            "agent_e": "app/catalog/products.py",
            "agent_f": "app/billing/invoices.py",
        },
        "agents": {
            "agent_a": {
                "intent": "I am implementing JWT-based user authentication for the API login flow.",
                "code": "# Agent A: login endpoints, password verification, JWT issuance.",
                "proposed_action": "Build API authentication endpoints for login and token issuance.",
            },
            "agent_b": {
                "intent": "I am building user sign-in and session validation for the same API.",
                "code": "# Agent B: sign-in handlers and session validation.",
                "proposed_action": "Build sign-in and session validation for authenticated API access.",
            },
            "agent_c": {
                "intent": "I am adding OAuth2 social login and token exchange to the auth module.",
                "code": "# Agent C: OAuth callbacks and token exchange.",
                "proposed_action": "Implement OAuth2 provider callbacks and token exchange.",
            },
            "agent_d": {
                "intent": "I am implementing product search, filtering, and pagination in the catalog.",
                "code": "# Agent D: search and filter API on products.",
                "proposed_action": "Add product search with filters and pagination.",
            },
            "agent_e": {
                "intent": "I am building the product listing API with sort and filters on the same catalog.",
                "code": "# Agent E: listing endpoints overlapping search.",
                "proposed_action": "Implement product listing with sort and filter parameters.",
            },
            "agent_f": {
                "intent": "I am implementing invoice creation, line items, and tax in billing.",
                "code": "# Agent F: invoice CRUD and tax calculation.",
                "proposed_action": "Build invoice creation with line items and tax totals.",
            },
        },
        "history": [],
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
