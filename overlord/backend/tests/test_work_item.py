from integrations.jira.component_map import resolve_file_path
from integrations.work_item import work_item_from_jira_issue


def test_resolve_file_path_from_component():
    mapping = {"Auth": "src/auth/"}
    assert resolve_file_path(components=["Auth"], labels=[], mapping=mapping) == "src/auth/"


def test_work_item_from_jira_issue_extracts_fields():
    issue = {
        "key": "PROJ-101",
        "fields": {
            "summary": "Add JWT middleware",
            "description": "Implement in src/auth/handlers.py",
            "components": [{"name": "Auth"}],
            "labels": ["overlord-ready"],
        },
    }
    item = work_item_from_jira_issue(
        issue, project_key="PROJ", component_mapping={"Auth": "src/auth/"}
    )
    assert item.external_id == "PROJ-101"
    assert item.title == "Add JWT middleware"
    assert item.file_path == "src/auth/handlers.py"
