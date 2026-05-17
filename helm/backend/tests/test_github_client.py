from integrations.github.client import GitHubClient


def test_mock_get_issue(monkeypatch):
    monkeypatch.setenv("GITHUB_MOCK", "1")
    monkeypatch.setenv("GITHUB_REPO", "AWSHacks-2026/MergeAI")
    client = GitHubClient.from_env()
    issue = client.get_issue(42)
    assert issue["number"] == 42
    assert "title" in issue
