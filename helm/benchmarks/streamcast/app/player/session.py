from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

_player_state: dict[str, Literal["playing", "paused"]] = {}


class PlayerState(BaseModel):
    stream_id: str
    state: Literal["playing", "paused"]


def register_routes(app) -> None:
    router = APIRouter(prefix="/player", tags=["player"])

    def _ensure_stream(stream_id: str) -> None:
        if stream_id not in _player_state:
            _player_state[stream_id] = "playing"

    @router.post("/{stream_id}/pause", response_model=PlayerState)
    def pause(stream_id: str) -> PlayerState:
        _ensure_stream(stream_id)
        _player_state[stream_id] = "paused"
        return PlayerState(stream_id=stream_id, state="paused")

    @router.post("/{stream_id}/resume", response_model=PlayerState)
    def resume(stream_id: str) -> PlayerState:
        _ensure_stream(stream_id)
        _player_state[stream_id] = "playing"
        return PlayerState(stream_id=stream_id, state="playing")

    @router.get("/{stream_id}/state", response_model=PlayerState)
    def state(stream_id: str) -> PlayerState:
        if stream_id not in _player_state:
            raise HTTPException(status_code=404, detail="Player session not found")
        return PlayerState(stream_id=stream_id, state=_player_state[stream_id])

    app.include_router(router)
