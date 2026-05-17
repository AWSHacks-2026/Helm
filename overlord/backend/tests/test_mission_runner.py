from unittest.mock import patch

from services.mission_runner import start_mission
from store.missions import MissionStore


@patch("services.mission_runner.knowledge_base.log_intent")
def test_start_mission_logs_intent(mock_log):
    store = MissionStore()
    m = store.create(session_id="s", title="JWT", file_path="src/auth/x.py")
    store.assign(m.mission_id, "agent_a")
    record = start_mission(store, mission_id=m.mission_id, agent_id="agent_a", session_id="s")
    assert record.status == "in_progress"
    mock_log.assert_called_once()
