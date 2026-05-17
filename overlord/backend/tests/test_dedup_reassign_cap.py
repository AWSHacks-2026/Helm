import os
from unittest.mock import patch

os.environ["OVERLORD_MOCK_BEDROCK"] = "1"

from bedrock.invoke_tracked import InvokeUsage
from agents.dedup_harness import run_dedup_benchmark


@patch("agents.dedup_harness.continuation_max_tokens", return_value=4096)
@patch("agents.dedup_harness.reassign_max_tokens", return_value=1024)
@patch("agents.dedup_harness.run_agent_edit")
def test_fleet_reassignments_use_lower_max_tokens(
    mock_edit, _mock_reassign_cap, _mock_continue_cap
):
    mock_edit.return_value = (
        "code\n",
        InvokeUsage("us.anthropic.claude-haiku-4-5-20251001-v1:0", "agent_a", 1, 1, 1),
    )

    run_dedup_benchmark("duplicate_work_fleet")

    caps = [call.kwargs["max_tokens"] for call in mock_edit.call_args_list]
    # 6 baseline (all full cap) + 3 continuations + 3 reassignments
    assert caps.count(4096) == 9
    assert caps.count(1024) == 3
