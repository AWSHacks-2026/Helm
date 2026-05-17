import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import server as helm_mcp  # noqa: E402


@patch.object(helm_mcp, "_client")
def test_helm_declare_intent_posts_to_api(mock_client_factory):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {"recorded": True}
    mock_client.post.return_value = mock_response
    mock_client.__enter__.return_value = mock_client
    mock_client_factory.return_value = mock_client

    result = helm_mcp.helm_declare_intent("s1", "a1", "f.py", "cache")
    assert result["recorded"] is True


@patch.object(helm_mcp, "_client")
def test_helm_record_checkpoint_posts_to_api(mock_client_factory):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {"recorded": True, "event_id": "e1"}
    mock_client.post.return_value = mock_response
    mock_client.__enter__.return_value = mock_client
    mock_client_factory.return_value = mock_client

    result = helm_mcp.helm_record_checkpoint("s1", "agent_a", "committed", "sha abc")
    assert result["recorded"] is True
    mock_client.post.assert_called_once()
