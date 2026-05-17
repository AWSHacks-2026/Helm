import os
from unittest.mock import patch

os.environ["HELM_MOCK_BEDROCK"] = "1"

from services.intent_alignment import maybe_align_on_declare
from store.sessions import SessionStore


def test_no_overlap_returns_recorded_only():
    store = SessionStore()
    out = maybe_align_on_declare(
        session_store=store,
        session_id="s",
        agent_id="a2",
        file_path="other.py",
        intent="billing",
    )
    assert out["overlap_detected"] is False
    assert out["alignment"] is None


@patch("services.intent_alignment.resolve_intent_conflict")
def test_overlap_invokes_alignment(mock_resolve):
    mock_resolve.return_value = {
        "conflict_type": "intent_conflict",
        "compatibility": "conflict",
        "unified_intent": "shared plan",
        "agent_updates": {"agent_a": "u1", "agent_b": "u2"},
        "resolved_code": "directive",
        "tokens_saved_estimate": "100 tokens saved (10%)",
        "reasoning": "overlap",
    }
    store = SessionStore()
    store.record_intent(session_id="s", agent_id="a1", file_path="f.py", intent="perf")
    out = maybe_align_on_declare(
        session_store=store,
        session_id="s",
        agent_id="a2",
        file_path="f.py",
        intent="minimal deps",
    )
    assert out["overlap_detected"] is True
    assert out["alignment"]["unified_intent"] == "shared plan"
