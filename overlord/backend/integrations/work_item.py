from __future__ import annotations

from dataclasses import dataclass

from integrations.jira.component_map import resolve_file_path


@dataclass(frozen=True)
class WorkItem:
    external_id: str
    source: str
    title: str
    description: str
    file_path: str
    labels: list[str]


def work_item_from_jira_issue(
    issue: dict,
    *,
    project_key: str,
    component_mapping: dict[str, str],
) -> WorkItem:
    _ = project_key
    key = issue.get("key", "")
    fields = issue.get("fields") or {}
    components = [c.get("name", "") for c in (fields.get("components") or []) if c.get("name")]
    labels = list(fields.get("labels") or [])
    description = fields.get("description") or ""
    if isinstance(description, dict):
        description = str(description)
    file_path = resolve_file_path(
        components=components,
        labels=labels,
        mapping=component_mapping,
        description=str(description),
    )
    return WorkItem(
        external_id=key,
        source="jira",
        title=str(fields.get("summary") or key),
        description=str(description),
        file_path=file_path,
        labels=labels,
    )
