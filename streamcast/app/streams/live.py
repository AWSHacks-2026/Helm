from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException

from app.streams.models import StreamCreate, StreamResponse

_streams: dict[str, dict[str, Any]] = {}


def register_routes(app) -> None:
    router = APIRouter(prefix="/streams", tags=["streams"])

    @router.post("", response_model=StreamResponse, status_code=201)
    def create_stream(body: StreamCreate) -> StreamResponse:
        stream_id = str(uuid.uuid4())
        record = {
            "id": stream_id,
            "title": body.title,
            "broadcaster": body.broadcaster,
            "is_live": False,
        }
        _streams[stream_id] = record
        return StreamResponse(**record)

    @router.get("/{stream_id}", response_model=StreamResponse)
    def get_stream(stream_id: str) -> StreamResponse:
        record = _streams.get(stream_id)
        if not record:
            raise HTTPException(status_code=404, detail="Stream not found")
        return StreamResponse(**record)

    @router.post("/{stream_id}/live", response_model=StreamResponse)
    def go_live(stream_id: str) -> StreamResponse:
        record = _streams.get(stream_id)
        if not record:
            raise HTTPException(status_code=404, detail="Stream not found")
        record["is_live"] = True
        return StreamResponse(**record)

    app.include_router(router)
