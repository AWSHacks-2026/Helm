"""Vinyl track catalog."""

from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass
class Track:
    title: str
    artist: str
    duration_sec: int

    def to_dict(self) -> dict:
        return asdict(self)


TRACKS: list[Track] = [
    Track("Kind of Blue", "Miles Davis", 567),
    Track("Blue in Green", "Miles Davis", 692),
]