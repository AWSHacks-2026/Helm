from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass

from botocore.exceptions import ClientError

from bedrock.client import get_bedrock_client
from bedrock.model_ids import resolve_inference_profile_id

_LAST_INVOKE_AT: float | None = None


@dataclass(frozen=True)
class InvokeUsage:
    model_id: str
    role: str
    input_tokens: int
    output_tokens: int
    latency_ms: int

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


def _mock_enabled() -> bool:
    return os.getenv("HELM_MOCK_BEDROCK") == "1"


def _min_invoke_interval_sec() -> float:
    return max(0.0, float(os.getenv("HELM_BEDROCK_MIN_INVOKE_INTERVAL_SEC", "0")))


def _throttle_max_retries() -> int:
    return max(1, int(os.getenv("HELM_BEDROCK_THROTTLE_MAX_RETRIES", "8")))


def _throttle_base_delay_sec() -> float:
    return max(0.5, float(os.getenv("HELM_BEDROCK_THROTTLE_BASE_SEC", "2")))


def _throttle_max_delay_sec() -> float:
    return max(_throttle_base_delay_sec(), float(os.getenv("HELM_BEDROCK_THROTTLE_MAX_SEC", "60")))


def _pace_before_invoke() -> None:
    global _LAST_INVOKE_AT
    interval = _min_invoke_interval_sec()
    if interval <= 0:
        return
    now = time.perf_counter()
    if _LAST_INVOKE_AT is not None:
        wait = interval - (now - _LAST_INVOKE_AT)
        if wait > 0:
            time.sleep(wait)
    _LAST_INVOKE_AT = time.perf_counter()


def _is_throttling_error(exc: BaseException) -> bool:
    name = type(exc).__name__
    if "Throttling" in name or "TooManyRequests" in name:
        return True
    if not isinstance(exc, ClientError):
        return False
    code = exc.response.get("Error", {}).get("Code", "")
    return code in {"ThrottlingException", "TooManyRequestsException", "ServiceUnavailableException"}


def invoke_anthropic_messages(
    *,
    model_id: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    role: str,
) -> tuple[str, InvokeUsage]:
    started = time.perf_counter()
    if _mock_enabled():
        text = messages[-1]["content"][:200]
        usage = InvokeUsage(
            model_id=model_id,
            role=role,
            input_tokens=len(json.dumps(messages)) // 4,
            output_tokens=len(text) // 4,
            latency_ms=int((time.perf_counter() - started) * 1000),
        )
        return f"# MOCK({role})\n{text}", usage

    resolved_id = resolve_inference_profile_id(model_id)
    client = get_bedrock_client()
    body = json.dumps(
        {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": messages,
        }
    )
    max_retries = _throttle_max_retries()
    last_error: BaseException | None = None
    for attempt in range(max_retries):
        _pace_before_invoke()
        try:
            response = client.invoke_model(modelId=resolved_id, body=body)
            break
        except ClientError as exc:
            last_error = exc
            if not _is_throttling_error(exc) or attempt >= max_retries - 1:
                raise
            delay = min(_throttle_max_delay_sec(), _throttle_base_delay_sec() * (2**attempt))
            time.sleep(delay)
    else:
        assert last_error is not None
        raise last_error

    payload = json.loads(response["body"].read())
    text = payload["content"][0]["text"]
    raw_usage = payload.get("usage") or {}
    usage = InvokeUsage(
        model_id=resolved_id,
        role=role,
        input_tokens=int(raw_usage.get("input_tokens", 0)),
        output_tokens=int(raw_usage.get("output_tokens", 0)),
        latency_ms=int((time.perf_counter() - started) * 1000),
    )
    return text, usage
