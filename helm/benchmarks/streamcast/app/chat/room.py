from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

_messages: dict[str, list[dict[str, Any]]] = {}
_last_post: dict[str, float] = {}
_RATE_LIMIT_SECONDS = 0.5


class ChatMessage(BaseModel):
    author: str = Field(min_length=1)
    body: str = Field(min_length=1, max_length=500)


class ChatMessageOut(ChatMessage):
    stream_id: str
    sent_at: float


def _rate_limit(stream_id: str) -> None:
    now = time.time()
    last = _last_post.get(stream_id, 0.0)
    if now - last < _RATE_LIMIT_SECONDS:
        raise HTTPException(status_code=429, detail="Rate limited")
    _last_post[stream_id] = now


def register_routes(app) -> None:
    router = APIRouter(prefix="/chat", tags=["chat"])

    @router.post("/{stream_id}/messages", response_model=ChatMessageOut, status_code=201)
    def post_message(stream_id: str, body: ChatMessage) -> ChatMessageOut:
        _rate_limit(stream_id)
        record = {
            "stream_id": stream_id,
            "author": body.author,
            "body": body.body,
            "sent_at": time.time(),
        }
        _messages.setdefault(stream_id, []).append(record)
        return ChatMessageOut(**record)

    @router.get("/{stream_id}/messages", response_model=list[ChatMessageOut])
    def list_messages(stream_id: str) -> list[ChatMessageOut]:
        return [ChatMessageOut(**m) for m in _messages.get(stream_id, [])]

    app.include_router(router)
