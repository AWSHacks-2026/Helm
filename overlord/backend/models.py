from typing import Literal

from pydantic import BaseModel


class AgentPayload(BaseModel):
    intent: str
    code: str
    proposed_action: str | None = None


class ResolutionPayload(BaseModel):
    conflict_type: Literal[
        "merge_conflict", "intent_conflict", "dependency_conflict"
    ]
    compatibility: Literal["conflict", "compatible"] | None = None
    reasoning: str
    unified_intent: str | None = None
    priority_order: list[str] | None = None
    agent_updates: dict[str, str] | None = None
    resolved_code: str
    tokens_saved_estimate: str
    history_used: list[str] | None = None


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
