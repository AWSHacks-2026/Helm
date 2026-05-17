import os

os.environ["HELM_MOCK_BEDROCK"] = "1"
os.environ["HELM_USE_LOCAL_MEMORY"] = "true"
os.environ["HELM_USE_LOCAL_POLICY"] = "true"

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_post_live_benchmark_merge_conflict():
    response = client.post(
        "/live/benchmark/merge_conflict",
        params={"seed_mode": "scenario"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["scenario"] == "merge_conflict"
    assert body["comparison"]["baseline_tokens"] > 0


def test_post_live_benchmark_unknown_404():
    response = client.post("/live/benchmark/not_real")
    assert response.status_code == 404
