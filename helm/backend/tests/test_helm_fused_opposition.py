import os

os.environ.setdefault("HELM_MOCK_BEDROCK", "1")

from helm import (
    coordinate_opposition_cluster,
    coordinate_opposition_fleet,
    _normalize_fleet_opposition_coord,
    _normalize_fused_opposition_coord,
)
from helm_prompt import build_fleet_opposition_coord_prompt, build_fused_opposition_coord_prompt


def test_build_fused_opposition_coord_prompt_includes_unified_intent_and_fleet_shape():
    prompt = build_fused_opposition_coord_prompt(
        {
            "agent_a": {"intent": "Use orjson for speed", "code": "", "proposed_action": ""},
            "agent_b": {"intent": "Remove dependencies", "code": "", "proposed_action": ""},
        },
        file_path="backend/app/auth.py",
    )
    assert "unified_intent" in prompt
    assert "continuations" in prompt
    assert "reassignments" in prompt
    assert "backend/app/auth.py" in prompt
    assert "orjson" in prompt


def test_build_fleet_opposition_coord_prompt_groups_by_file():
    agents = {
        "agent_a": {"intent": "JWT only", "code": "", "proposed_action": ""},
        "agent_b": {"intent": "cookies only", "code": "", "proposed_action": ""},
        "agent_c": {"intent": "search", "code": "", "proposed_action": ""},
    }
    paths = {
        "agent_a": "backend/app/routers/auth.py",
        "agent_b": "backend/app/routers/auth.py",
        "agent_c": "backend/app/routers/listings.py",
    }
    prompt = build_fleet_opposition_coord_prompt(agents, paths)
    assert "unified_intents" in prompt
    assert "auth.py" in prompt
    assert "listings.py" in prompt


def test_coordinate_opposition_fleet_mock(monkeypatch):
    monkeypatch.setenv("HELM_MOCK_BEDROCK", "1")
    agents = {
        "agent_a": {"intent": "A", "code": "", "proposed_action": "A"},
        "agent_b": {"intent": "B", "code": "", "proposed_action": "B"},
    }
    paths = {
        "agent_a": "backend/app/routers/auth.py",
        "agent_b": "backend/app/routers/auth.py",
    }
    raw = coordinate_opposition_fleet(agents, paths)
    assert raw["conflict_type"] == "opposition_coord_fleet"
    assert "backend/app/routers/auth.py" in raw["unified_intents"]


def test_coordinate_opposition_cluster_mock_returns_fused_plan(monkeypatch):
    monkeypatch.setenv("HELM_MOCK_BEDROCK", "1")
    agents = {
        "agent_a": {"intent": "A", "code": "", "proposed_action": "A"},
        "agent_b": {"intent": "B", "code": "", "proposed_action": "B"},
    }
    raw = coordinate_opposition_cluster(agents, file_path="auth.py")
    assert raw["conflict_type"] == "opposition_coord"
    assert raw["unified_intent"]
    assert raw["continuations"]
    assert raw["reassignments"]
    assert set(raw["continuations"]) | {r["agent_id"] for r in raw["reassignments"]} == {
        "agent_a",
        "agent_b",
    }


def test_normalize_fused_opposition_coord_requires_unified_intent():
    raw = {
        "duplicate_detected": True,
        "continuations": ["agent_a"],
        "reassignments": [{"agent_id": "agent_b", "suggested_new_task": "audit logs"}],
        "reasoning": "ok",
        "unified_intent": "Prefer stdlib cache before new deps.",
    }
    out = _normalize_fused_opposition_coord(raw, {"agent_a", "agent_b"})
    assert out["unified_intent"] == "Prefer stdlib cache before new deps."
    assert out["conflict_type"] == "opposition_coord"
