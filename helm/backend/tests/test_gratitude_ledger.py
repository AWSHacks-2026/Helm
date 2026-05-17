from services.gratitude_ledger import build_gratitude_ledger


def test_ledger_aggregates_events():
    events = [
        {
            "event_type": "guardrail_blocked",
            "payload": {"agent_id": "b", "file_path": "f.py"},
            "timestamp": "2026-01-01T00:00:00Z",
        },
        {
            "event_type": "mission_delegated",
            "payload": {
                "duplicate_detected": True,
                "tokens_saved_estimate": "~1,800",
                "assignments": [{"action": "reassign", "assigned_agent_id": "b"}],
            },
            "timestamp": "2026-01-01T00:01:00Z",
        },
        {
            "event_type": "intent_aligned",
            "payload": {"tokens_saved_estimate": "~1,080", "inference_tier": "haiku"},
            "timestamp": "2026-01-01T00:02:00Z",
        },
    ]
    ledger = build_gratitude_ledger(events)
    assert ledger.guardrails_blocked == 1
    assert ledger.duplicates_avoided == 1
    assert ledger.tokens_saved_total >= 2880
    assert "2,880" in ledger.tokens_saved_display
    assert ledger.haiku_calls == 1
