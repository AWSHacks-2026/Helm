from __future__ import annotations

import os
import time
from typing import Any

import jwt
from fastapi import APIRouter, HTTPException

from app.auth.models import TokenResponse, UserLogin, UserRegister

_users: dict[str, dict[str, Any]] = {}
_JWT_SECRET = os.environ.get("STREAMCAST_JWT_SECRET", "streamcast-dev-secret")
_JWT_ALG = "HS256"


def _issue_token(email: str) -> str:
    return jwt.encode(
        {"sub": email, "exp": int(time.time()) + 3600},
        _JWT_SECRET,
        algorithm=_JWT_ALG,
    )


def register_routes(app) -> None:
    router = APIRouter(prefix="/auth", tags=["auth"])

    @router.post("/register", response_model=TokenResponse)
    def register(body: UserRegister) -> TokenResponse:
        if body.email in _users:
            raise HTTPException(status_code=409, detail="User already exists")
        _users[body.email] = {"email": body.email, "password": body.password}
        return TokenResponse(access_token=_issue_token(body.email))

    @router.post("/login", response_model=TokenResponse)
    def login(body: UserLogin) -> TokenResponse:
        user = _users.get(body.email)
        if not user or user["password"] != body.password:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return TokenResponse(access_token=_issue_token(body.email))

    app.include_router(router)
