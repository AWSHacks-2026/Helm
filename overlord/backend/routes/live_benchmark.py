from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Query

from agents.live_harness import run_benchmark
from agents.merge_scenarios import get_pairwise_merge_scenario_names

router = APIRouter(prefix="/live", tags=["live-benchmark"])


@router.get("/benchmark/scenarios")
def list_benchmark_scenarios() -> list[str]:
    return get_pairwise_merge_scenario_names()


@router.post("/benchmark/{scenario_name}")
def post_live_benchmark(
    scenario_name: str,
    seed_mode: str = Query(default="scenario", pattern="^(scenario|haiku)$"),
):
    if scenario_name not in get_pairwise_merge_scenario_names():
        raise HTTPException(status_code=404, detail="Merge scenario not found")
    try:
        return run_benchmark(scenario_name, seed_mode=seed_mode)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
