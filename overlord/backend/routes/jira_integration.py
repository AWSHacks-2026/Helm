from __future__ import annotations

import json
import os

from fastapi import APIRouter, Header, HTTPException, Request

from integrations.jira.client import JiraClient
from integrations.work_item import work_item_from_jira_issue
from models import JiraWebhookPayload, MissionSummary
from session.team_session import resolve_team_session_id

router = APIRouter(prefix="/integrations/jira", tags=["jira"])


def _component_mapping() -> dict[str, str]:
    raw = os.getenv("JIRA_COMPONENT_FILE_MAP", "{}")
    return json.loads(raw)


def _upsert_mission_from_issue(request: Request, issue: dict, session_id: str) -> MissionSummary:
    store = request.app.state.mission_store
    item = work_item_from_jira_issue(
        issue,
        project_key=os.getenv("JIRA_PROJECT_KEY", "PROJ"),
        component_mapping=_component_mapping(),
    )
    existing = store.find_by_external_id(item.external_id) if item.external_id else None
    if existing:
        return store.to_summary(existing)
    record = store.create(
        session_id=session_id,
        title=item.title,
        description=item.description,
        file_path=item.file_path,
        external_id=item.external_id,
        source="jira",
    )
    return store.to_summary(record)


@router.post("/webhook", response_model=MissionSummary)
async def jira_webhook(
    payload: JiraWebhookPayload,
    request: Request,
    session_id: str | None = None,
    x_overlord_secret: str | None = Header(default=None, alias="X-Overlord-Secret"),
) -> MissionSummary:
    expected = os.getenv("JIRA_WEBHOOK_SECRET", "")
    if expected and x_overlord_secret != expected:
        raise HTTPException(status_code=401, detail="invalid webhook secret")
    sid = session_id or resolve_team_session_id()
    return _upsert_mission_from_issue(request, payload.issue, sid)


@router.post("/sync/{issue_key}", response_model=MissionSummary)
async def sync_issue(
    issue_key: str,
    request: Request,
    session_id: str | None = None,
) -> MissionSummary:
    client = JiraClient.from_env()
    issue = client.get_issue(issue_key)
    sid = session_id or resolve_team_session_id()
    return _upsert_mission_from_issue(request, issue, sid)
