from models import AgentPayload, ResolutionPayload, ResolveResponse


def test_resolution_payload_requires_merge_fields():
    r = ResolutionPayload(
        conflict_type="merge_conflict",
        reasoning="Merged cache and type hints.",
        resolved_code="def get_user(user_id: str) -> User: ...",
        tokens_saved_estimate="~2400",
    )
    assert r.conflict_type == "merge_conflict"


def test_resolution_payload_allows_duplicate_work_fields():
    resolution = ResolutionPayload(
        conflict_type="duplicate_work",
        reasoning=(
            "Both agents are implementing the same authentication flow, so Agent A "
            "should continue and Agent B should move to audit logging."
        ),
        resolved_code="",
        tokens_saved_estimate="~1800",
        duplicate_detected=True,
        agent_to_continue="agent_a",
        agent_to_reassign="agent_b",
        suggested_new_task="Implement audit logging for authentication events.",
    )

    assert resolution.conflict_type == "duplicate_work"
    assert resolution.duplicate_detected is True
    assert resolution.agent_to_continue == "agent_a"
    assert resolution.agent_to_reassign == "agent_b"
    assert (
        resolution.suggested_new_task
        == "Implement audit logging for authentication events."
    )


def test_resolve_response_shape():
    resp = ResolveResponse(
        agent_a=AgentPayload(intent="a", code="code_a"),
        agent_b=AgentPayload(intent="b", code="code_b"),
        resolution=ResolutionPayload(
            conflict_type="merge_conflict",
            reasoning="r",
            resolved_code="merged",
            tokens_saved_estimate="100",
        ),
    )
    assert resp.agent_a.intent == "a"
