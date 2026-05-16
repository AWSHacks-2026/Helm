"""Feeding schedule for multiple tanks."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class FeedingEvent:
    tank_id: str
    food_grams: int
    at: datetime


@dataclass
class FeedingSchedule:
    events: list[FeedingEvent] = field(default_factory=list)

    def add_feeding(self, tank_id: str, food_grams: int, at: datetime | None = None) -> None:
        self.events.append(
            FeedingEvent(
                tank_id=tank_id,
                food_grams=food_grams,
                at=at or datetime.utcnow(),
            )
        )