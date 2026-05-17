from __future__ import annotations

import json
import re
from typing import Any


_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    fence_match = _FENCE_RE.search(stripped)
    if fence_match:
        stripped = fence_match.group(1).strip()

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in model output")

    return json.loads(stripped[start : end + 1])
