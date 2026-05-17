from __future__ import annotations

from dataclasses import dataclass, field

from tqdm import tqdm

from bedrock.invoke_tracked import InvokeUsage


@dataclass
class TimestepTracker:
    """Progress bar that advances only on Bedrock-backed LLM calls."""

    desc: str
    total_llm_calls: int | None = None
    _bar: tqdm = field(init=False, repr=False)
    cumulative_input: int = 0
    cumulative_output: int = 0
    last_llm_ms: int = 0
    llm_call_count: int = 0

    def __post_init__(self) -> None:
        self._bar = tqdm(total=self.total_llm_calls, desc=self.desc, unit="llm")

    def record_llm(self, usage: InvokeUsage, *, phase: str) -> None:
        self.cumulative_input += usage.input_tokens
        self.cumulative_output += usage.output_tokens
        self.last_llm_ms = usage.latency_ms
        self.llm_call_count += 1
        total = self.cumulative_input + self.cumulative_output
        self._bar.set_postfix(
            phase=phase,
            llm_ms=self.last_llm_ms,
            tokens=total,
            llm_n=self.llm_call_count,
            refresh=False,
        )
        self._bar.update(1)

    def note_phase(self, *, phase: str) -> None:
        """Non-LLM milestone (intent, guardrail, git commit); label only, no bar tick."""
        total = self.cumulative_input + self.cumulative_output
        self._bar.set_postfix(
            phase=phase,
            llm_ms=self.last_llm_ms,
            tokens=total,
            llm_n=self.llm_call_count,
            refresh=False,
        )

    def record_usage(self, usage: InvokeUsage, *, phase: str) -> None:
        self.record_llm(usage, phase=phase)

    def close(self) -> None:
        self._bar.close()
