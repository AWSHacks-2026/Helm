from models import AgentPayload, ResolutionPayload, ResolveResponse


def test_resolution_payload_requires_merge_fields():
    r = ResolutionPayload(
        conflict_type="merge_conflict",
        reasoning="Merged cache and type hints.",
        resolved_code="def get_user(user_id: str) -> User: ...",
        tokens_saved_estimate="~2400",
    )
    assert r.conflict_type == "merge_conflict"


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
