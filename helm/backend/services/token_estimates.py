from __future__ import annotations

import re


def parse_tokens_estimate(value: str | None) -> int:
    if not value:
        return 0
    match = re.search(r"~?(\d[\d,]*)", value)
    if not match:
        return 0
    return int(match.group(1).replace(",", ""))
