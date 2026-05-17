from store.missions import MissionStore


def test_create_and_list_by_session():
    store = MissionStore()
    m = store.create(
        session_id="sess-1",
        title="JWT",
        file_path="src/auth/x.py",
        external_id="PROJ-1",
        source="github",
    )
    listed = store.list_summaries(session_id="sess-1")
    assert len(listed) == 1
    assert listed[0].mission_id == m.mission_id
    assert listed[0].status == "queued"
