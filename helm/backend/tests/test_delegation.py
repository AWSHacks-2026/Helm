from unittest.mock import patch

from services.delegation import delegate_missions
from store.missions import MissionStore


@patch("services.delegation.detect_duplication")
def test_delegate_pairwise_overlap(mock_dedup):
    mock_dedup.return_value = {
        "duplicate_detected": True,
        "agent_to_continue": "agent_a",
        "agent_to_reassign": "agent_b",
        "suggested_new_task": "Add rate limiting instead",
        "reasoning": "overlap on auth",
        "conflict_type": "duplicate_work",
        "resolved_code": "",
        "tokens_saved_estimate": "~500",
    }
    store = MissionStore()
    m1 = store.create(
        session_id="s",
        title="A",
        file_path="src/auth/x.py",
        preferred_agent_id="agent_a",
    )
    m2 = store.create(
        session_id="s",
        title="B",
        file_path="src/auth/x.py",
        preferred_agent_id="agent_b",
    )
    result = delegate_missions(store, session_id="s", use_llm_dedup=True)
    assert result["duplicate_detected"] is True
    assert store.get(m1.mission_id).assigned_agent_id == "agent_a"
    assert store.get(m2.mission_id).assigned_agent_id == "agent_b"
    assert "rate limiting" in (store.get(m2.mission_id).suggested_task or "")


@patch("services.delegation.detect_duplication")
def test_delegate_uses_thanksgiving_queue_over_llm_task(mock_dedup):
    mock_dedup.return_value = {
        "duplicate_detected": True,
        "agent_to_continue": "agent_a",
        "agent_to_reassign": "agent_b",
        "suggested_new_task": "LLM generic task",
        "reasoning": "overlap",
        "conflict_type": "duplicate_work",
        "resolved_code": "",
        "tokens_saved_estimate": "~500",
    }
    store = MissionStore()
    store.create(session_id="s", title="A", file_path="src/auth/x.py")
    store.create(session_id="s", title="B", file_path="src/auth/x.py")
    backlog = store.create(
        session_id="s", title="Billing", file_path="app/billing/invoices.py"
    )
    result = delegate_missions(store, session_id="s", use_llm_dedup=True)
    reassigned = [a for a in result["assignments"] if a.get("action") == "reassign"]
    assert reassigned
    assert store.get(backlog.mission_id).assigned_agent_id == "agent_b"
    assert reassigned[0]["assignment_source"] == "thanksgiving_queue"


@patch("services.delegation.detect_duplication")
def test_delegate_skips_dedup_when_disjoint_files(mock_dedup, monkeypatch):
    monkeypatch.setenv("HELM_GATE_ENABLED", "1")
    store = MissionStore()
    store.create(session_id="s", title="A", file_path="src/auth/x.py")
    store.create(session_id="s", title="B", file_path="src/billing/y.py")
    delegate_missions(store, session_id="s", use_llm_dedup=True)
    mock_dedup.assert_not_called()
