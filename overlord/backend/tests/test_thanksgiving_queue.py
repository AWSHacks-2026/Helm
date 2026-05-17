from services.thanksgiving_queue import pick_backlog_mission
from store.missions import MissionStore


def test_picks_queued_mission_on_different_file():
    store = MissionStore()
    store.create(session_id="s", title="Auth", file_path="src/user.py")
    backlog = store.create(
        session_id="s",
        title="Billing",
        file_path="app/billing/invoices.py",
    )
    picked = pick_backlog_mission(
        store, session_id="s", exclude_file_paths={"src/user.py"}
    )
    assert picked is not None
    assert picked.mission_id == backlog.mission_id


def test_returns_none_when_no_backlog():
    store = MissionStore()
    store.create(session_id="s", title="Only", file_path="src/user.py")
    assert (
        pick_backlog_mission(store, session_id="s", exclude_file_paths={"src/user.py"})
        is None
    )
