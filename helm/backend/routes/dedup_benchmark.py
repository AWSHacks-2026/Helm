from __future__ import annotations

from fastapi import APIRouter, HTTPException

from agents.dedup_harness import get_dedup_scenario_names, run_dedup_benchmark

router = APIRouter(prefix="/live", tags=["dedup-benchmark"])


@router.get("/benchmark/dedup/scenarios")
def list_dedup_scenarios() -> list[str]:
    return get_dedup_scenario_names()


@router.post("/benchmark/dedup/{scenario_name}")
def post_dedup_benchmark(scenario_name: str):
    if scenario_name not in get_dedup_scenario_names():
        raise HTTPException(status_code=404, detail="Dedup scenario not found")
    try:
        return run_dedup_benchmark(scenario_name)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
