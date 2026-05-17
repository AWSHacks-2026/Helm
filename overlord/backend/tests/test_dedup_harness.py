import os

os.environ["OVERLORD_MOCK_BEDROCK"] = "1"

from agents.dedup_harness import run_dedup_benchmark


def test_dedup_fleet_benchmark_mock_shows_impl_savings():
    result = run_dedup_benchmark("duplicate_work_fleet")
    c = result["comparison"]

    assert c["overlord_duplicate_detected"] is True
    assert c["baseline_full_implementation_runs"] == 6
    assert c["overlord_full_implementation_runs"] == 3
    assert c["duplicate_implementations_avoided"] == 3
    assert len(result["overlord"]["continuations"]) == 3
    assert len(result["overlord"]["reassignments"]) == 3


def test_dedup_pairwise_benchmark_mock_still_works():
    result = run_dedup_benchmark("duplicate_work")
    c = result["comparison"]

    assert c["baseline_full_implementation_runs"] == 2
    assert c["overlord_full_implementation_runs"] == 1
    assert c["duplicate_implementations_avoided"] == 1
