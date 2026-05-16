import shutil

from bedrock import knowledge_base


def test_append_and_list_history(tmp_path, monkeypatch):
    monkeypatch.setattr(knowledge_base, "DATA_DIR", tmp_path)
    knowledge_base.append_event(
        "sess_kb",
        {
            "event_type": "intent_declared",
            "payload": {"agent_id": "a1", "file_path": "f.py", "intent": "cache"},
        },
    )
    history = knowledge_base.list_history("sess_kb")
    assert len(history) == 1
    assert history[0]["event_type"] == "intent_declared"
    shutil.rmtree(tmp_path)
