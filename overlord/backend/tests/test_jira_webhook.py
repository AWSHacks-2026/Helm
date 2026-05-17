import json

from fastapi.testclient import TestClient

from main import app


def test_webhook_rejects_bad_secret(monkeypatch):
    monkeypatch.setenv("JIRA_WEBHOOK_SECRET", "sekrit")
    monkeypatch.setenv("JIRA_MOCK", "1")
    client = TestClient(app)
    resp = client.post(
        "/integrations/jira/webhook",
        headers={"X-Overlord-Secret": "wrong"},
        json={"issue": {"key": "PROJ-9", "fields": {"summary": "x", "labels": []}}},
    )
    assert resp.status_code == 401


def test_webhook_upserts_mission(monkeypatch):
    monkeypatch.setenv("JIRA_WEBHOOK_SECRET", "sekrit")
    monkeypatch.setenv("JIRA_MOCK", "1")
    monkeypatch.setenv("JIRA_COMPONENT_FILE_MAP", json.dumps({"Auth": "src/auth/"}))
    client = TestClient(app)
    resp = client.post(
        "/integrations/jira/webhook",
        headers={"X-Overlord-Secret": "sekrit"},
        params={"session_id": "jira-wh"},
        json={
            "issue": {
                "key": "PROJ-9",
                "fields": {
                    "summary": "Auth task",
                    "description": "details",
                    "components": [{"name": "Auth"}],
                    "labels": ["overlord-ready"],
                },
            },
        },
    )
    assert resp.status_code == 200
    assert resp.json()["external_id"] == "PROJ-9"
