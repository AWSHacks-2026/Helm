from unittest.mock import MagicMock, patch

from agents.shopfix_harness import run_shopfix_case


@patch("agents.shopfix_harness.httpx.post")
@patch("agents.shopfix_harness.run_verify")
def test_helm_disjoint_records_intents(mock_verify, mock_post, tmp_path):
    mock_post.return_value = MagicMock(
        status_code=200,
        json=lambda: {"contention": {"gate_tier": "allow", "contention_detected": False}},
    )
    mock_post.return_value.raise_for_status = lambda: None
    mock_verify.return_value = MagicMock(returncode=0)

    result = run_shopfix_case(
        suite="disjoint",
        agent_count=2,
        mode="helm",
        work_dir=tmp_path,
        use_patches=False,
        helm_api="http://test",
    )
    assert mock_post.call_count == 2
    assert result["gate_skipped_count"] == 2
    assert result["tests_pass"] is True
