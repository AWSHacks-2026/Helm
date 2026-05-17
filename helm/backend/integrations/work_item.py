from __future__ import annotations

from dataclasses import dataclass

from integrations.path_map import resolve_file_path


@dataclass(frozen=True)
class WorkItem:
    external_id: str
    source: str
    title: str
    description: str
    file_path: str
    labels: list[str]


def work_item_from_github_issue(
    issue: dict,
    *,
    repo: str,
    label_mapping: dict[str, str],
) -> WorkItem:
    number = issue.get("number", 0)
    labels = [lb.get("name", "") for lb in (issue.get("labels") or []) if lb.get("name")]
    body = str(issue.get("body") or "")
    return WorkItem(
        external_id=f"{repo}#{number}",
        source="github",
        title=str(issue.get("title") or f"Issue {number}"),
        description=body,
        file_path=resolve_file_path(
            components=[],
            labels=labels,
            mapping=label_mapping,
            description=body,
        ),
        labels=labels,
    )


def github_issue_has_ready_label(issue: dict, ready_label: str) -> bool:
    names = {lb.get("name", "") for lb in (issue.get("labels") or [])}
    return ready_label in names
