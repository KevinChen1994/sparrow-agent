from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

from sparrow_agent.core.runtime import AgentRuntime

app = FastAPI(title="Sparrow Agent")
runtime = AgentRuntime()
WEB_ROOT = Path(__file__).resolve().parents[1] / "web"


class ChatRequest(BaseModel):
    session_id: str
    message: str


@app.get("/api/session/{session_id}")
def start_session(session_id: str) -> dict:
    result = runtime.start_session(session_id=session_id)
    return result.model_dump(mode="json")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chat")
def chat(payload: ChatRequest) -> dict:
    result = runtime.run_turn(session_id=payload.session_id, user_input=payload.message)
    return result.model_dump(mode="json")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_ROOT / "index.html")
