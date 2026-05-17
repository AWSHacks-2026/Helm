import hashlib
import hmac
import json

from fastapi.testclient import TestClient

from main import app


def _sign(body: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def test_webhook_rejects_bad_signature(monkeypatch):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "sekrit")
    monkeypatch.setenv("GITHUB_MOCK", "1")
    monkeypatch.setenv("GITHUB_REPO", "AWSHacks-2026/MergeAI")
    client = TestClient(app)
    body = json.dumps(
        {"action": "opened", "issue": {"number": 1, "title": "t", "body": "", "labels": []}}
    ).encode()
    resp = client.post(
        "/integrations/github/webhook",
        content=body,
        headers={"X-Hub-Signature-256": "sha256=bad", "Content-Type": "application/json"},
    )
    assert resp.status_code == 401


def test_webhook_upserts_labeled_issue(monkeypatch):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "sekrit")
    monkeypatch.setenv("GITHUB_MOCK", "1")
    monkeypatch.setenv("GITHUB_REPO", "AWSHacks-2026/MergeAI")
    monkeypatch.setenv("GITHUB_READY_LABEL", "helm-ready")
    monkeypatch.setenv("GITHUB_LABEL_FILE_MAP", json.dumps({"auth": "src/auth/"}))
    payload = {
        "action": "labeled",
        "issue": {
            "number": 9,
            "title": "Auth task",
            "body": "details",
            "labels": [{"name": "auth"}, {"name": "helm-ready"}],
        },
    }
    body = json.dumps(payload).encode()
    client = TestClient(app)
    resp = client.post(
        "/integrations/github/webhook",
        content=body,
        headers={
            "X-Hub-Signature-256": _sign(body, "sekrit"),
            "Content-Type": "application/json",
        },
        params={"session_id": "gh-wh"},
    )
    assert resp.status_code == 200
    assert resp.json()["external_id"] == "AWSHacks-2026/MergeAI#9"
