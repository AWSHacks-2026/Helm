"""Unit tests for ShopFix live helm execution plan (no Bedrock)."""

import pytest

from agents.shopfix_live_benchmark import (
    _build_helm_execution_plan,
    _disjoint_assignments,
    _fused_coord_enabled,
    _reassign_enabled,
    _trim_dedup_plan,
)
from agents.shopfix_scenarios import (
    assignment_for_reassign,
    load_assignments,
    load_base_modules,
)


def test_reassign_maps_to_disjoint_fill_file():
    assignments = load_assignments("contention", agent_count=4)
    auth_file = "backend/app/routers/auth.py"
    reserved = {auth_file}
    original = next(a for a in assignments if a.agent_id == "agent_b")
    mapped = assignment_for_reassign(
        original,
        "Work on cart checkout flow",
        suite="contention",
        modules=load_base_modules(),
        reserved_files=reserved,
    )
    assert mapped.primary_file != auth_file
    assert mapped.agent_id == "agent_b"


def test_build_plan_only_runs_continuations_and_reassigns():
    assignments = load_assignments("contention", agent_count=4)
    run_by_id, reassign_ids, full_runs = _build_helm_execution_plan(
        "contention",
        assignments,
        continuations=["agent_a", "agent_d"],
        reassignments=[
            {"agent_id": "agent_b", "suggested_new_task": "Improve cart API"},
            {"agent_id": "agent_c", "suggested_new_task": "Improve orders API"},
        ],
    )
    assert set(run_by_id.keys()) == {"agent_a", "agent_b", "agent_c", "agent_d"}
    assert reassign_ids == {"agent_b", "agent_c"}
    assert full_runs == 2
    assert run_by_id["agent_b"].primary_file != run_by_id["agent_a"].primary_file
    assert run_by_id["agent_c"].primary_file != run_by_id["agent_a"].primary_file


def test_trim_dedup_skips_extra_cluster_losers():
    assignments = load_assignments("contention", agent_count=4)
    cont, reassign, skipped = _trim_dedup_plan(
        assignments,
        continuations=["agent_a", "agent_d"],
        reassignments=[
            {"agent_id": "agent_b", "suggested_new_task": "Cart work"},
            {"agent_id": "agent_c", "suggested_new_task": "Orders work"},
        ],
        suite="contention",
    )
    assert set(cont) == {"agent_a", "agent_d"}
    assert len(reassign) == 1
    assert reassign[0]["agent_id"] in {"agent_b", "agent_c"}
    assert len(skipped) == 1
    assert skipped[0] in {"agent_b", "agent_c"}
    assert skipped[0] != reassign[0]["agent_id"]


@pytest.mark.skip(reason="requires second contested cluster in tasks.yaml (listings hotspot)")
def test_trim_dedup_n6_two_clusters():
    assignments = load_assignments("contention", agent_count=6)
    cont, reassign, skipped = _trim_dedup_plan(
        assignments,
        continuations=["agent_a", "agent_d", "agent_f"],
        reassignments=[
            {"agent_id": "agent_b", "suggested_new_task": "t1"},
            {"agent_id": "agent_c", "suggested_new_task": "t2"},
            {"agent_id": "agent_e", "suggested_new_task": "t3"},
        ],
        suite="contention",
    )
    assert "agent_a" in cont
    assert "agent_d" in cont
    assert "agent_f" in cont
    assert len(reassign) == 2
    assert len(skipped) == 1


def test_disjoint_assignments_for_contention_n4():
    assignments = load_assignments("contention", agent_count=4)
    disjoint = _disjoint_assignments(assignments)
    assert len(disjoint) == 1
    assert disjoint[0].agent_id == "agent_d"


def test_trim_dedup_no_reassign_when_disabled(monkeypatch):
    monkeypatch.setenv("SHOPFIX_REASSIGN", "0")
    assignments = load_assignments("contention", agent_count=4)
    cont, reassign, skipped = _trim_dedup_plan(
        assignments,
        continuations=["agent_a", "agent_d"],
        reassignments=[
            {"agent_id": "agent_b", "suggested_new_task": "Cart work"},
            {"agent_id": "agent_c", "suggested_new_task": "Orders work"},
        ],
        suite="contention",
    )
    assert set(cont) == {"agent_a", "agent_d"}
    assert reassign == []
    assert set(skipped) == {"agent_b", "agent_c"}


def test_intent_opposition_n4_balanced_two_agents_per_contested_file():
    assignments = load_assignments("intent_opposition", agent_count=4)
    auth = "backend/app/routers/auth.py"
    listings = "backend/app/routers/listings.py"
    by_file: dict[str, list] = {}
    for a in assignments:
        by_file.setdefault(a.primary_file, []).append(a)
    assert len(by_file[auth]) == 2
    assert len(by_file[listings]) == 2
    assert by_file[auth][0].intent != by_file[auth][1].intent
    assert by_file[listings][0].intent != by_file[listings][1].intent


def test_intent_opposition_n6_has_auth_and_listings_clusters():
    assignments = load_assignments("intent_opposition", agent_count=6)
    auth = "backend/app/routers/auth.py"
    listings = "backend/app/routers/listings.py"
    auth_agents = [a for a in assignments if a.primary_file == auth]
    listing_agents = [a for a in assignments if a.primary_file == listings]
    fill_agents = [
        a for a in assignments if a.primary_file not in {auth, listings}
    ]
    assert len(auth_agents) == 2
    assert len(listing_agents) == 2
    assert len(fill_agents) == 2
    assert auth_agents[0].intent != auth_agents[1].intent


def test_opposition_trim_skips_losers_without_reassign_by_default(monkeypatch):
    monkeypatch.delenv("SHOPFIX_REASSIGN", raising=False)
    assignments = load_assignments("intent_opposition", agent_count=4)
    cont, reassign, skipped = _trim_dedup_plan(
        assignments,
        continuations=["agent_a", "agent_c"],
        reassignments=[{"agent_id": "agent_b", "suggested_new_task": "fill task"}],
        suite="intent_opposition",
    )
    assert reassign == []
    assert set(skipped) == {"agent_b", "agent_d"}
    assert _reassign_enabled("intent_opposition") is False
    monkeypatch.setenv("SHOPFIX_REASSIGN", "1")
    assert _reassign_enabled("intent_opposition") is True
    assert _reassign_enabled("contention") is True
    monkeypatch.setenv("SHOPFIX_REASSIGN", "0")
    assert _reassign_enabled("contention") is False


def test_fused_coord_default_only_for_intent_opposition(monkeypatch):
    monkeypatch.delenv("SHOPFIX_FUSED_COORD", raising=False)
    assert _fused_coord_enabled("intent_opposition") is True
    assert _fused_coord_enabled("contention") is False
    monkeypatch.setenv("SHOPFIX_FUSED_COORD", "0")
    assert _fused_coord_enabled("intent_opposition") is False
