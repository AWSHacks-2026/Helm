"""Minimal constellation name → star count lookup (no cache)."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import settings


@dataclass(frozen=True)
class ConstellationInfo:
    name: str
    star_count: int
    brightest: str


_CATALOG: dict[str, ConstellationInfo] = {
    "Orion": ConstellationInfo("Orion", 42, "Betelgeuse"),
    "Ursa Major": ConstellationInfo("Ursa Major", 7, "Alioth"),
    "Crux": ConstellationInfo("Crux", 4, "Acrux"),
}


def lookup_constellation(name: str) -> ConstellationInfo | None:
    key = name.strip()
    if not key:
        return None
    return _CATALOG.get(key)