import pytest

from main import app
from store.conflicts import ConflictStore
from store.sessions import SessionStore
from ws.hub import ConnectionManager


@pytest.fixture(autouse=True)
def _init_app_state():
    app.state.conflict_store = ConflictStore()
    app.state.session_store = SessionStore()
    app.state.ws_hub = ConnectionManager()
    yield
