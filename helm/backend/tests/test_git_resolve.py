from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app


@patch("routes.git_resolve.arbitrate")
def test_git_merge_conflict(mock_arb):
    mock_arb.return_value = {
        "conflict_type": "merge_conflict",
        "reasoning": "merged",
        "resolved_code": "def f(): pass",
        "tokens_saved_estimate": "~100",
    }
    client = TestClient(app)
    response = client.post(
        "/integrations/git/merge-conflict",
        json={
            "session_id": "git-demo",
            "file_path": "src/user.py",
            "ours": "def get_user():\n    return cache.get()",
            "theirs": "def get_user() -> User:\n    return db.query()",
        },
    )
    assert response.status_code == 200
    assert response.json()["resolution"]["conflict_type"] == "merge_conflict"
    mock_arb.assert_called_once()
