from fastapi.testclient import TestClient

from main import app


def test_create_and_list_missions():
    client = TestClient(app)
    created = client.post(
        "/missions",
        json={"session_id": "jira-test", "title": "Auth", "file_path": "src/auth/x.py"},
    )
    assert created.status_code == 200
    listed = client.get("/missions", params={"session_id": "jira-test"})
    assert listed.status_code == 200
    assert len(listed.json()) >= 1
