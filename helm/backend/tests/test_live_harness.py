import os

os.environ["HELM_MOCK_BEDROCK"] = "1"
os.environ["HELM_USE_LOCAL_MEMORY"] = "true"
os.environ["HELM_USE_LOCAL_POLICY"] = "true"

from agents.live_harness import run_benchmark
from agents.merge_scenarios import get_merge_scenario


def test_run_benchmark_returns_baseline_and_helm_paths():
    result = run_benchmark("merge_conflict", seed_mode="scenario")
    assert result["scenario"] == "merge_conflict"
    assert "baseline" in result
    assert "helm" in result
    assert "comparison" in result
    assert result["baseline"]["usage"]["total_tokens"] > 0
    assert result["helm"]["usage"]["total_tokens"] >= 0


def test_run_benchmark_uses_same_seed_for_both_paths():
    result = run_benchmark("merge_conflict", seed_mode="scenario")
    scenario = get_merge_scenario("merge_conflict")
    assert result["artifact"]["agent_a"]["code"] == scenario["agent_a"]["code"]
