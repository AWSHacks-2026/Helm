from models import MissionCreateRequest


def test_mission_create_defaults_session():
    req = MissionCreateRequest(title="Auth work", file_path="src/auth/x.py")
    assert req.session_id
    assert req.external_id is None
