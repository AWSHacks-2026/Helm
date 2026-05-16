from __future__ import annotations

from fastapi import APIRouter

from models import GitMergeConflictRequest, GitMergeConflictResponse, ResolutionPayload
from overlord import arbitrate

router = APIRouter(prefix="/integrations/git", tags=["git"])


@router.post("/merge-conflict", response_model=GitMergeConflictResponse)
def resolve_git_merge_conflict(payload: GitMergeConflictRequest) -> GitMergeConflictResponse:
    agent_a = {
        "intent": f"Git side ours ({payload.agent_a_id})",
        "code": payload.ours,
    }
    agent_b = {
        "intent": f"Git side theirs ({payload.agent_b_id})",
        "code": payload.theirs,
    }
    kb = [{"text": f"merge base:\n{payload.base}"}] if payload.base else None
    raw = arbitrate(
        agent_a,
        agent_b,
        kb_context=kb,
        session_id=payload.session_id,
    )
    return GitMergeConflictResponse(
        session_id=payload.session_id,
        file_path=payload.file_path,
        resolution=ResolutionPayload.model_validate(raw),
    )
