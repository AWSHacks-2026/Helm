from fastapi import FastAPI

from app.auth.handlers import register_routes as register_auth
from app.chat.room import register_routes as register_chat
from app.player.session import register_routes as register_player
from app.streams.live import register_routes as register_streams

app = FastAPI(title="Streamcast", version="0.1.0")


@app.get("/health")
def health():
    return {"status": "ok"}


register_auth(app)
register_streams(app)
register_player(app)
register_chat(app)
