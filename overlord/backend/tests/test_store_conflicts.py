from store.conflicts import ConflictStore


def _resolution():
    return {
        "conflict_type": "merge_conflict",
        "reasoning": "r",
        "resolved_code": "z",
        "tokens_saved_estimate": "1",
    }


def test_create_and_get_conflict():
    store = ConflictStore()
    record = store.create(
        session_id="sess_1",
        file_path="a.py",
        agent_a_id="agent_a",
        agent_b_id="agent_b",
        conflict_type="merge_conflict",
        agent_a_payload={"intent": "a", "code": "x"},
        agent_b_payload={"intent": "b", "code": "y"},
        resolution_payload=_resolution(),
    )
    fetched = store.get(record.conflict_id)
    assert fetched is not None
    assert fetched.status == "pending_approval"


def test_list_by_session_filters_status():
    store = ConflictStore()
    store.create(
        session_id="sess_1",
        file_path="a.py",
        agent_a_id="a",
        agent_b_id="b",
        conflict_type="merge_conflict",
        agent_a_payload={"intent": "a", "code": "x"},
        agent_b_payload={"intent": "b", "code": "y"},
        resolution_payload=_resolution(),
    )
    items = store.list_summaries(session_id="sess_1", status="pending_approval")
    assert len(items) == 1
    assert items[0].session_id == "sess_1"


def test_approve_updates_status():
    store = ConflictStore()
    record = store.create(
        session_id="sess_1",
        file_path="a.py",
        agent_a_id="a",
        agent_b_id="b",
        conflict_type="merge_conflict",
        agent_a_payload={"intent": "a", "code": "x"},
        agent_b_payload={"intent": "b", "code": "y"},
        resolution_payload=_resolution(),
    )
    updated = store.set_status(record.conflict_id, "approved")
    assert updated.status == "approved"
