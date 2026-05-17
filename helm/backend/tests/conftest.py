import os

import pytest

os.environ.setdefault("HELM_USE_LOCAL_MEMORY", "true")
os.environ.setdefault("HELM_USE_LOCAL_POLICY", "true")

from main import app
from store.conflicts import ConflictStore
from store.missions import MissionStore
from store.sessions import SessionStore
from ws.hub import ConnectionManager


@pytest.fixture(autouse=True)
def _init_app_state():
    app.state.conflict_store = ConflictStore()
    app.state.mission_store = MissionStore()
    app.state.session_store = SessionStore()
    app.state.ws_hub = ConnectionManager()
    yield
