from __future__ import annotations

import re


def resolve_file_path(
    *,
    components: list[str],
    labels: list[str],
    mapping: dict[str, str],
    description: str = "",
) -> str:
    match = re.search(r"(?:src|lib|app)/[\w./-]+\.(?:py|ts|tsx|js|go|rs)", description)
    if match:
        return match.group(0)
    for name in components:
        if name in mapping:
            return mapping[name]
    for label in labels:
        key = label.lower()
        if key in mapping:
            return mapping[key]
        if label in mapping:
            return mapping[label]
    return ""
