from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from session.team_session import resolve_team_session_id


class AgentPayload(BaseModel):
    intent: str
    code: str
    proposed_action: str | None = None


class ResolutionPayload(BaseModel):
    conflict_type: Literal[
        "merge_conflict", "intent_conflict", "dependency_conflict", "duplicate_work"
    ]
    compatibility: Literal["conflict", "compatible"] | None = None
    reasoning: str
    unified_intent: str | None = None
    priority_order: list[str] | None = None
    agent_updates: dict[str, str] | None = None
    resolved_code: str
    tokens_saved_estimate: str
    history_used: list[str] | None = None
    duplicate_detected: bool | None = None
    agent_to_continue: str | None = None
    agent_to_reassign: str | None = None
    suggested_new_task: str | None = None


class ResolveResponse(BaseModel):
    agent_a: AgentPayload
    agent_b: AgentPayload
    resolution: ResolutionPayload


class BedrockArbitrationResult(BaseModel):
    """Raw JSON shape we ask Sonnet to return."""

    conflict_type: str
    reasoning: str
    resolved_code: str
    tokens_saved_estimate: str


class AgentPayloadWithId(AgentPayload):
    agent_id: str


ConflictStatus = Literal["pending_approval", "approved", "rejected", "auto_applied"]


class LiveResolveRequest(BaseModel):
    session_id: str = Field(default_factory=resolve_team_session_id)
    file_path: str
    agent_a: AgentPayloadWithId
    agent_b: AgentPayloadWithId


class LiveResolveResponse(ResolveResponse):
    conflict_id: str
    session_id: str
    file_path: str
    status: ConflictStatus


class IntentRecordRequest(BaseModel):
    session_id: str = Field(default_factory=resolve_team_session_id)
    agent_id: str
    file_path: str
    intent: str


class IntentRecordResponse(BaseModel):
    recorded: bool = True


class GuardrailCheckRequest(BaseModel):
    session_id: str = Field(default_factory=resolve_team_session_id)
    agent_id: str
    file_path: str
    action: Literal["read", "write", "delete"]
    proposed_code: str = ""


class GuardrailCheckResponse(BaseModel):
    allowed: bool
    reason: str = ""
    route_to_overlord: bool = False
    conflict_id: str | None = None


class HistoryEvent(BaseModel):
    event_id: str
    session_id: str
    timestamp: str
    event_type: Literal[
        "intent_declared",
        "guardrail_blocked",
        "conflict_resolved",
        "conflict_approved",
    ]
    payload: dict


class ConflictSummary(BaseModel):
    conflict_id: str
    session_id: str
    file_path: str
    status: ConflictStatus
    conflict_type: str
    created_at: str
    agent_a_id: str = ""
    agent_b_id: str = ""


class ConflictApproveRequest(BaseModel):
    approved: bool


class ConflictApproveResponse(BaseModel):
    conflict_id: str
    status: ConflictStatus


class ConflictDetailResponse(BaseModel):
    conflict_id: str
    session_id: str
    file_path: str
    status: ConflictStatus
    agent_a: AgentPayloadWithId
    agent_b: AgentPayloadWithId
    resolution: ResolutionPayload


class GitMergeConflictRequest(BaseModel):
    session_id: str = Field(default_factory=resolve_team_session_id)
    file_path: str
    agent_a_id: str = "git_ours"
    agent_b_id: str = "git_theirs"
    ours: str
    theirs: str
    base: str | None = None


class GitMergeConflictResponse(BaseModel):
    session_id: str
    file_path: str
    resolution: ResolutionPayload
