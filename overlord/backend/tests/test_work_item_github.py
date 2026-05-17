from integrations.work_item import work_item_from_github_issue


def test_work_item_from_github_issue():
    issue = {
        "number": 42,
        "title": "Add JWT middleware",
        "body": "Implement in src/auth/handlers.py",
        "labels": [{"name": "auth"}, {"name": "overlord-ready"}],
    }
    item = work_item_from_github_issue(
        issue,
        repo="AWSHacks-2026/MergeAI",
        label_mapping={"auth": "src/auth/"},
    )
    assert item.external_id == "AWSHacks-2026/MergeAI#42"
    assert item.source == "github"
    assert item.title == "Add JWT middleware"
    assert item.file_path == "src/auth/handlers.py"
    assert "overlord-ready" in item.labels
