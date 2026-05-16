import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

os.environ["OVERLORD_MOCK_BEDROCK"] = "1"

from main import app  # noqa: E402

client = TestClient(app)


@pytest.fixture(autouse=True)
def _ensure_mock_bedrock():
    os.environ["OVERLORD_MOCK_BEDROCK"] = "1"
    yield


def test_resolve_intent_conflict_returns_intent_type():
    r = client.post("/resolve/intent_conflict")
    assert r.status_code == 200
    assert r.json()["resolution"]["conflict_type"] == "intent_conflict"


def test_resolve_guardrail_scenario_returns_400():
    r = client.post("/resolve/guardrail_prevention")
    assert r.status_code == 400
    assert "guardrail/check" in r.json()["detail"]
