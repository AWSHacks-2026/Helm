"""API router wiring auth, catalog, and billing."""

from __future__ import annotations

from fastapi import APIRouter

api_router = APIRouter(prefix="/api/v1")
