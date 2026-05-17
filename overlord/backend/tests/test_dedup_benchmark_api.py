import os

os.environ["OVERLORD_MOCK_BEDROCK"] = "1"

from fastapi.testclient import TestClient

from main import app  # noqa: E402

client = TestClient(app)


def test_post_dedup_benchmark_duplicate_work():
    r = client.post("/live/benchmark/dedup/duplicate_work")
    assert r.status_code == 200
    body = r.json()
    assert body["scenario"] == "duplicate_work"
    assert body["comparison"]["overlord_duplicate_detected"] is True
    assert body["comparison"]["duplicate_implementations_avoided"] == 1
