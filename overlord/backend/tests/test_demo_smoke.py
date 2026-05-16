import os

import pytest
from fastapi.testclient import TestClient

os.environ["OVERLORD_MOCK_BEDROCK"] = "1"

from main import app  # noqa: E402

client = TestClient(app)


@pytest.fixture(autouse=True)
def _ensure_mock_bedrock():
    os.environ["OVERLORD_MOCK_BEDROCK"] = "1"
    yield


def test_demo_smoke_all_pass():
    r = client.get("/demo/smoke")
    assert r.status_code == 200
    body = r.json()
    assert body["all_passed"] is True
    names = {c["scenario"] for c in body["checks"]}
    assert names == {"merge_conflict", "intent_conflict", "guardrail_prevention"}
    for check in body["checks"]:
        assert check["passed"] is True, check


def test_root_lists_demo_smoke():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["demo_smoke"] == "/demo/smoke"
