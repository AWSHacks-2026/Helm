"""Authentication handlers — agents converge here without Overlord."""

from __future__ import annotations

# Base stub: agents extend with login, JWT, sessions, OAuth, etc.


def health_check() -> dict[str, str]:
    return {"status": "auth_module_ready"}
