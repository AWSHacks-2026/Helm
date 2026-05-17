from __future__ import annotations

from fastapi import APIRouter, HTTPException

from agents.merge_fleet_harness import (
    get_merge_fleet_scenario_names,
    run_merge_fleet_benchmark,
)

router = APIRouter(prefix="/live", tags=["merge-fleet-benchmark"])


@router.get("/benchmark/merge-fleet/scenarios")
def list_merge_fleet_scenarios() -> list[str]:
    return get_merge_fleet_scenario_names()


@router.post("/benchmark/merge-fleet/{scenario_name}")
def post_merge_fleet_benchmark(scenario_name: str):
    if scenario_name not in get_merge_fleet_scenario_names():
        raise HTTPException(status_code=404, detail="Merge fleet scenario not found")
    try:
        return run_merge_fleet_benchmark(scenario_name)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
