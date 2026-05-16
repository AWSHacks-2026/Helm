from unittest.mock import MagicMock, patch

from bedrock.client import get_bedrock_agent_client, get_bedrock_client


@patch("bedrock.client.boto3.client")
def test_get_bedrock_client_uses_runtime_and_region(mock_boto_client):
    mock_boto_client.return_value = MagicMock()
    client = get_bedrock_client()
    mock_boto_client.assert_called_once_with(
        service_name="bedrock-runtime",
        region_name="us-east-1",
    )
    assert client is mock_boto_client.return_value


@patch("bedrock.client.boto3.client")
def test_get_bedrock_agent_client_uses_agent_runtime(mock_boto_client):
    mock_boto_client.return_value = MagicMock()
    client = get_bedrock_agent_client()
    mock_boto_client.assert_called_once_with(
        service_name="bedrock-agent-runtime",
        region_name="us-east-1",
    )
    assert client is mock_boto_client.return_value
