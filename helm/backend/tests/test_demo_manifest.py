from fastapi.testclient import TestClient

from main import app
from routes.demo_manifest import build_manifest

client = TestClient(app)


def test_benchmark_manifest_endpoint():
    response = client.get("/demo/benchmark-manifest")
    assert response.status_code == 200
    body = response.json()
    assert "pillars" in body
    contention = body["pillars"]["contention"]
    assert contention["cost_savings_pct"] == 18
    assert contention["wall_savings_pct"] == 39


def test_build_manifest_defaults_without_file(tmp_path):
    missing = tmp_path / "missing.json"
    manifest = build_manifest(missing)
    assert manifest["pillars"]["contention"]["cost_savings_pct"] == 18
