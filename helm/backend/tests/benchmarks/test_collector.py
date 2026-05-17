import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from benchmarks.collector import collect_run


def test_collect_run_writes_report_json(tmp_path: Path):
    run_id = "20260517-test"
    run_dir = tmp_path / run_id
    run_dir.mkdir()
    (run_dir / "meta.json").write_text(
        json.dumps(
            {
                "suite": "independent",
                "helm_enabled": False,
                "started_at": 0.0,
                "ended_at": 10.0,
                "merge_success": True,
                "git_conflict_files": 0,
            }
        ),
        encoding="utf-8",
    )

    mock_client = MagicMock()
    history_resp = MagicMock()
    history_resp.json.return_value = []
    gratitude_resp = MagicMock()
    gratitude_resp.json.return_value = {"tokens_saved_display": "0"}
    mock_client.get.side_effect = [history_resp, gratitude_resp]
    mock_client.__enter__.return_value = mock_client

    with patch("benchmarks.collector.httpx.Client", return_value=mock_client):
        report = collect_run(
            run_id=run_id,
            results_dir=tmp_path,
            api_base="http://127.0.0.1:8000",
            session_id="streamcast-ind-test",
        )

    assert report.suite == "independent"
    assert (tmp_path / run_id / "report.json").exists()
