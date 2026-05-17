from __future__ import annotations

import hashlib
import hmac
import json
import os

from fastapi import APIRouter, HTTPException, Request

from integrations.github.client import GitHubClient
from integrations.work_item import github_issue_has_ready_label, work_item_from_github_issue
from models import MissionSummary
from session.team_session import resolve_team_session_id

router = APIRouter(prefix="/integrations/github", tags=["github"])


def _label_mapping() -> dict[str, str]:
    raw = os.getenv("GITHUB_LABEL_FILE_MAP", "{}")
    return json.loads(raw)


def _ready_label() -> str:
    return os.getenv("GITHUB_READY_LABEL", "overlord-ready")


def _verify_signature(body: bytes, signature: str | None) -> None:
    secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")
    if not secret:
        return
    if not signature or not signature.startswith("sha256="):
        raise HTTPException(status_code=401, detail="missing webhook signature")
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature[7:], expected):
        raise HTTPException(status_code=401, detail="invalid webhook signature")


def _should_ingest(action: str, issue: dict) -> bool:
    ready = _ready_label()
    if action in {"opened", "labeled", "reopened"}:
        return github_issue_has_ready_label(issue, ready)
    return False


def _upsert_mission_from_issue(request: Request, issue: dict, session_id: str) -> MissionSummary:
    store = request.app.state.mission_store
    repo = os.getenv("GITHUB_REPO", "mergeai/default")
    item = work_item_from_github_issue(issue, repo=repo, label_mapping=_label_mapping())
    existing = store.find_by_external_id(item.external_id) if item.external_id else None
    if existing:
        return store.to_summary(existing)
    record = store.create(
        session_id=session_id,
        title=item.title,
        description=item.description,
        file_path=item.file_path,
        external_id=item.external_id,
        source="github",
    )
    return store.to_summary(record)


@router.post("/webhook", response_model=MissionSummary)
async def github_webhook(request: Request, session_id: str | None = None) -> MissionSummary:
    body = await request.body()
    _verify_signature(body, request.headers.get("X-Hub-Signature-256"))
    payload = json.loads(body)
    action = str(payload.get("action", ""))
    issue = payload.get("issue") or {}
    if not _should_ingest(action, issue):
        raise HTTPException(status_code=202, detail="ignored: missing ready label")
    sid = session_id or resolve_team_session_id()
    return _upsert_mission_from_issue(request, issue, sid)


@router.post("/sync/{issue_number}", response_model=MissionSummary)
async def sync_issue(
    issue_number: int,
    request: Request,
    session_id: str | None = None,
) -> MissionSummary:
    client = GitHubClient.from_env()
    issue = client.get_issue(issue_number)
    sid = session_id or resolve_team_session_id()
    return _upsert_mission_from_issue(request, issue, sid)
