import pytest

from bedrock.contention_gate import assess_dedup, assess_intent
from store.sessions import SessionStore


@pytest.fixture(autouse=True)
def gate_on(monkeypatch):
    monkeypatch.setenv("HELM_GATE_ENABLED", "1")
    monkeypatch.setenv("HELM_GATE_FORCE", "0")
    monkeypatch.setenv("HELM_GATE_MIN_AGENTS", "2")


def test_gate_disabled_always_arbitrate(monkeypatch):
    monkeypatch.setenv("HELM_GATE_ENABLED", "0")
    store = SessionStore()
    result = assess_dedup(
        store,
        "s",
        agents={"a": {}, "b": {}},
        file_paths={"a": "x.py", "b": "y.py"},
    )
    assert result.gate_tier == "arbitrate"


def test_disjoint_fleet_allow():
    store = SessionStore()
    sid = "happy"
    paths = {
        "agent_a": "app/auth/handlers.py",
        "agent_b": "app/catalog/products.py",
        "agent_c": "app/billing/invoices.py",
    }
    for aid, path in paths.items():
        store.record_intent(session_id=sid, agent_id=aid, file_path=path, intent=f"work on {path}")
    agents = {k: {"intent": "x"} for k in paths}
    result = assess_dedup(store, sid, agents=agents, file_paths=paths)
    assert result.gate_tier == "allow"
    assert result.contention_detected is False
    assert result.signals == []


def test_three_agents_same_file_arbitrate():
    store = SessionStore()
    sid = "fleet"
    file_paths = {f"agent_{c}": "app/auth/handlers.py" for c in "abc"}
    for aid in file_paths:
        store.record_intent(
            session_id=sid, agent_id=aid, file_path="app/auth/handlers.py", intent="auth"
        )
    agents = {k: {"intent": "auth"} for k in file_paths}
    result = assess_dedup(store, sid, agents=agents, file_paths=file_paths)
    assert result.gate_tier == "arbitrate"
    assert "file_cluster:app/auth/handlers.py:3" in result.signals


def test_intent_overlap_on_same_file_arbitrate():
    store = SessionStore()
    sid = "intent"
    store.record_intent(
        session_id=sid,
        agent_id="agent_a",
        file_path="m.py",
        intent="Optimize performance with caching",
    )
    result = assess_intent(
        store,
        sid,
        agent_id="agent_b",
        file_path="m.py",
        intent="Minimize dependencies and remove caching",
    )
    assert result.gate_tier == "arbitrate"
    assert result.contention_kind == "intent"
