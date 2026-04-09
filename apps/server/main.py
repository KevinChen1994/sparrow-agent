from __future__ import annotations

import asyncio
import json
import queue
import threading
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from sparrow_agent.core.runtime import AgentRuntime
from sparrow_agent.schemas.models import TraceStep

app = FastAPI(title="Sparrow Agent")
runtime = AgentRuntime()
WEB_ROOT = Path(__file__).resolve().parents[1] / "web"


class ChatRequest(BaseModel):
    session_id: str
    message: str
    show_thinking: bool = False


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
    if not payload.show_thinking:
        result = result.model_copy(update={"trace_steps": []})
    return result.model_dump(mode="json")


def _encode_sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


@app.post("/api/chat/stream")
async def chat_stream(payload: ChatRequest) -> StreamingResponse:
    events: "queue.Queue[tuple[str, dict]]" = queue.Queue()
    done = threading.Event()

    def emit(event: str, data: dict) -> None:
        events.put((event, data))

    def on_trace(step: TraceStep) -> None:
        emit("trace", step.model_dump(mode="json"))

    def on_response_event(event: str, data: dict) -> None:
        emit(event, data)

    def worker() -> None:
        try:
            result = runtime.run_turn(
                session_id=payload.session_id,
                user_input=payload.message,
                trace_callback=on_trace if payload.show_thinking else None,
                response_event_callback=on_response_event,
            )
            if not payload.show_thinking:
                result = result.model_copy(update={"trace_steps": []})
            emit("final", result.model_dump(mode="json"))
        except Exception as exc:  # pragma: no cover
            emit("error", {"message": str(exc)})
        finally:
            done.set()

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    async def event_stream():
        yield _encode_sse("start", {"session_id": payload.session_id})
        while not done.is_set() or not events.empty():
            try:
                event, data = events.get(timeout=0.1)
            except queue.Empty:
                await asyncio.sleep(0.05)
                continue
            yield _encode_sse(event, data)
        yield _encode_sse("done", {"ok": True})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_ROOT / "index.html")
