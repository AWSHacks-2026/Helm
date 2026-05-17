from services.handoff import build_gratitude_handoff
from store.missions import MissionStore
from store.sessions import SessionStore


def test_handoff_includes_owner_intent_and_backlog_mission():
    sessions = SessionStore()
    missions = MissionStore()
    sessions.record_intent(
        session_id="s", agent_id="agent_a", file_path="src/user.py", intent="JWT auth"
    )
    missions.create(
        session_id="s",
        title="Billing invoices",
        file_path="app/billing/invoices.py",
    )
    handoff = build_gratitude_handoff(
        session_id="s",
        blocked_agent_id="agent_b",
        file_path="src/user.py",
        session_store=sessions,
        mission_store=missions,
    )
    assert handoff.owner_agent_id == "agent_a"
    assert "JWT" in handoff.owner_intent
    assert handoff.suggested_file_path == "app/billing/invoices.py"
    assert handoff.suggested_mission_id is not None
    assert "thanks" in handoff.message.lower() or "thank" in handoff.message.lower()
