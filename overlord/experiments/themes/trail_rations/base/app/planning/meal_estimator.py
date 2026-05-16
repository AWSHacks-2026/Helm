"""Backpacking meal calorie estimator."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Meal:
    name: str
    servings: int = 1

    def as_dict(self) -> dict:
        return {"name": self.name, "servings": self.servings}


@dataclass
class DayPlan:
    day: str
    meals: list[Meal] = field(default_factory=list)
    daily_total: int = 0

    def add_meal(self, name: str, servings: int = 1) -> None:
        self.meals.append(Meal(name=name, servings=servings))


def create_plan(days: list[str]) -> DayPlan:
    return DayPlan(day=days[0] if days else "day1", meals=[])