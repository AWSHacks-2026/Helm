from models import (
    AgentPayloadWithId,
    ConflictSummary,
    GuardrailCheckResponse,
    LiveResolveRequest,
)


def test_live_resolve_request_requires_session_and_agents():
    req = LiveResolveRequest(
        session_id="sess_1",
        file_path="src/user.py",
        agent_a=AgentPayloadWithId(agent_id="a1", intent="i1", code="c1"),
        agent_b=AgentPayloadWithId(agent_id="a2", intent="i2", code="c2"),
    )
    assert req.file_path.endswith("user.py")


def test_guardrail_response_blocks_when_not_allowed():
    resp = GuardrailCheckResponse(
        allowed=False,
        reason="overlap",
        route_to_helm=True,
        conflict_id=None,
    )
    assert resp.route_to_helm is True


def test_conflict_summary_status_literal():
    c = ConflictSummary(
        conflict_id="id1",
        session_id="sess_1",
        file_path="f.py",
        status="pending_approval",
        conflict_type="merge_conflict",
        created_at="2026-05-17T00:00:00Z",
    )
    assert c.status == "pending_approval"
