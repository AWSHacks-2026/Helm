import os

os.environ["OVERLORD_MOCK_BEDROCK"] = "1"

from experiments.metrics import summarize_run
from experiments.runner import run_all_themes


def test_run_all_themes_mock_produces_metrics():
    results = run_all_themes(mock=True)
    assert len(results) == 4
    summaries = [summarize_run(r) for r in results]
    for row in summaries:
        assert row["conflict_edits"] >= 1
        assert row["total_tokens"] > 0
        assert row["resolution_time_ms"] > 0
        assert row["successful_build_rate"] == 1.0
