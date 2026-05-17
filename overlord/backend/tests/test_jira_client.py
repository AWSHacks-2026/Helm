from integrations.jira.client import JiraClient


def test_mock_client_returns_canned_issue(monkeypatch):
    monkeypatch.setenv("JIRA_MOCK", "1")
    client = JiraClient.from_env()
    issue = client.get_issue("PROJ-101")
    assert issue["key"] == "PROJ-101"
