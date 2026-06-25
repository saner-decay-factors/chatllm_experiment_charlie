from __future__ import annotations

from pathlib import Path

from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text

from backend.database import Base, engine
from backend.routers.chat import router as chat_router


Base.metadata.create_all(bind=engine)

# Migration: ensure columns exist on chat_messages
inspector = inspect(engine)
msg_columns = {c["name"] for c in inspector.get_columns("chat_messages")}
if "session_id" not in msg_columns:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE chat_messages ADD COLUMN session_id INTEGER REFERENCES chat_sessions(id)"))
if "session_key" not in msg_columns:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE chat_messages ADD COLUMN session_key VARCHAR(120) DEFAULT 'default'"))

app = FastAPI(title="ChatLLM Experiment API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response: Response = await call_next(request)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response


app.add_middleware(NoCacheMiddleware)

app.include_router(chat_router)

NO_CACHE_HEADERS = {
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0",
}

ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"

if FRONTEND_DIR.exists():
    app.mount("/frontend", StaticFiles(directory=FRONTEND_DIR), name="frontend")


@app.get("/")
def root() -> FileResponse:
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="frontend/index.html nao encontrado")
    return FileResponse(index_path, headers=NO_CACHE_HEADERS)
