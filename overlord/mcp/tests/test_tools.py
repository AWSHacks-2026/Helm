import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import server as overlord_mcp  # noqa: E402


@patch.object(overlord_mcp, "_client")
def test_overlord_declare_intent_posts_to_api(mock_client_factory):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {"recorded": True}
    mock_client.post.return_value = mock_response
    mock_client.__enter__.return_value = mock_client
    mock_client_factory.return_value = mock_client

    result = overlord_mcp.overlord_declare_intent("s1", "a1", "f.py", "cache")
    assert result["recorded"] is True
