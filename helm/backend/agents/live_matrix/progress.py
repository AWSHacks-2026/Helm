from __future__ import annotations

from dataclasses import dataclass, field

from tqdm import tqdm

from bedrock.invoke_tracked import InvokeUsage


@dataclass
class TimestepTracker:
    desc: str
    total_timesteps: int | None = None
    _bar: tqdm = field(init=False, repr=False)
    cumulative_input: int = 0
    cumulative_output: int = 0

    def __post_init__(self) -> None:
        self._bar = tqdm(total=self.total_timesteps, desc=self.desc, unit="step")

    def record_usage(self, usage: InvokeUsage, *, phase: str) -> None:
        self.record_timestep(
            phase=phase,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            latency_ms=usage.latency_ms,
        )

    def record_timestep(
        self,
        *,
        phase: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        latency_ms: int = 0,
    ) -> None:
        self.cumulative_input += input_tokens
        self.cumulative_output += output_tokens
        total = self.cumulative_input + self.cumulative_output
        self._bar.set_postfix(phase=phase, tokens=total, latency_ms=latency_ms, refresh=False)
        self._bar.update(1)

    def close(self) -> None:
        self._bar.close()
