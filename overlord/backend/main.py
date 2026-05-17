from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.conflicts import router as conflicts_router
from routes.demo_smoke import router as demo_smoke_router
from routes.guardrail_demo import router as guardrail_demo_router
from routes.git_resolve import router as git_resolve_router
from routes.guardrails import router as guardrails_router
from routes.health import router as health_router
from routes.history import router as history_router
from routes.intents import router as intents_router
from routes.dedup_benchmark import router as dedup_benchmark_router
from routes.live_benchmark import router as live_benchmark_router
from routes.merge_fleet_benchmark import router as merge_fleet_benchmark_router
from routes.merge_lab import router as merge_lab_router
from routes.resolve import router as resolve_router
from routes.gratitude import router as gratitude_router
from routes.jira_integration import router as jira_integration_router
from routes.missions import router as missions_router
from store.conflicts import ConflictStore
from store.missions import MissionStore
from store.sessions import SessionStore
from ws.hub import ConnectionManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.conflict_store = ConflictStore()
    app.state.mission_store = MissionStore()
    app.state.session_store = SessionStore()
    app.state.ws_hub = ConnectionManager()
    yield


app = FastAPI(title="Overlord", version="0.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(resolve_router)
app.include_router(merge_lab_router)
app.include_router(live_benchmark_router)
app.include_router(dedup_benchmark_router)
app.include_router(merge_fleet_benchmark_router)
app.include_router(intents_router)
app.include_router(git_resolve_router)
app.include_router(guardrails_router)
app.include_router(guardrail_demo_router)
app.include_router(demo_smoke_router)
app.include_router(conflicts_router)
app.include_router(history_router)
app.include_router(missions_router)
app.include_router(gratitude_router)
app.include_router(jira_integration_router)
