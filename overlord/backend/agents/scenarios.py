from bedrock.guardrails import GUARDRAIL_DEMO_SCENARIO

SCENARIO_META: dict[str, dict[str, str]] = {
    "merge_conflict": {
        "kind": "merge",
        "title": "Act 1 — Cache vs readability (get_user)",
        "description": "Two agents edited the same function differently.",
    },
    "intent_conflict": {
        "kind": "intent",
        "title": "Act 2 — Performance vs minimal dependencies",
        "description": "Contradictory goals before code diverges.",
    },
    "guardrail_prevention": {
        "kind": "guardrail",
        "title": "Act 3 — Block delete of peer's cache utility",
        "description": "Use POST /guardrail/check (not /resolve) for full flow.",
    },
}

SCENARIOS: dict[str, dict] = {
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
        "agent_a": {
            "intent": "I am optimizing this module for maximum performance",
            "code": """
# module: data_access.py
# Plan: add in-memory cache + connection pooling for all DB reads
CACHE_TTL = 300
_pool = None

def get_user(user_id: str):
    return _cached_fetch("user", user_id)
""".strip(),
        },
        "agent_b": {
            "intent": "I am refactoring this module to minimize dependencies",
            "code": """
# module: data_access.py
# Plan: remove cache layer and third-party pool; use stdlib only
import sqlite3

def get_user(user_id: str):
    with sqlite3.connect("app.db") as conn:
        return conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
""".strip(),
        },
    },
    "guardrail_prevention": {
        "agent_a": GUARDRAIL_DEMO_SCENARIO["agent_a"],
        "agent_b": GUARDRAIL_DEMO_SCENARIO["agent_b"],
    },
}


def get_scenario_kind(name: str) -> str:
    return SCENARIO_META[name]["kind"]
