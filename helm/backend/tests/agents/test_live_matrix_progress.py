from agents.live_matrix.progress import TimestepTracker
from bedrock.invoke_tracked import InvokeUsage


def test_tracker_llm_only_advances_bar():
    updates: list[int] = []
    postfixes: list[dict] = []

    class FakeBar:
        def set_postfix(self, **kwargs):
            postfixes.append(kwargs)

        def update(self, n=1):
            updates.append(n)

        def close(self):
            pass

    tracker = TimestepTracker(desc="test", total_llm_calls=3)
    tracker._bar = FakeBar()
    tracker.note_phase(phase="intent")
    assert updates == []
    usage = InvokeUsage(
        model_id="haiku",
        role="agent_a",
        input_tokens=100,
        output_tokens=40,
        latency_ms=120,
    )
    tracker.record_llm(usage, phase="edit")
    assert updates == [1]
    assert postfixes[-1]["llm_ms"] == 120
    assert postfixes[-1]["tokens"] == 140
    assert postfixes[-1]["llm_n"] == 1
