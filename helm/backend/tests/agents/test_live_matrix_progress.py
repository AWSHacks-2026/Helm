from agents.live_matrix.progress import TimestepTracker


def test_tracker_accumulates_tokens():
    steps: list[dict] = []

    class FakeBar:
        def set_postfix(self, **kwargs):
            steps.append(kwargs)

        def update(self, n=1):
            pass

        def close(self):
            pass

    tracker = TimestepTracker(desc="test", total_timesteps=5)
    tracker._bar = FakeBar()
    tracker.record_timestep(phase="edit", input_tokens=100, output_tokens=40, latency_ms=120)
    assert steps[-1]["tokens"] == 140
    assert steps[-1]["latency_ms"] == 120
