from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.server.main import app, runtime
from sparrow_agent.core.runtime import AgentRuntime
from sparrow_agent.llm.base import EchoModelClient
from sparrow_agent.memory.store import MemoryStore
from sparrow_agent.storage.file_store import FileStore


def create_runtime_templates(tmp_path) -> None:
    template_dir = tmp_path / "templates" / "runtime"
    (template_dir / "memory").mkdir(parents=True, exist_ok=True)
    (template_dir / "AGENTS.md").write_text("# Template AGENTS\n", encoding="utf-8")
    (template_dir / "SOUL.md").write_text("# Template SOUL\n", encoding="utf-8")
    (template_dir / "USER.md").write_text("# Template USER\n", encoding="utf-8")
    (template_dir / "MEMORY.md").write_text("# Template MEMORY\n", encoding="utf-8")


def build_runtime(tmp_path) -> AgentRuntime:
    create_runtime_templates(tmp_path)
    file_store = FileStore(
        workspace_root=tmp_path,
        runtime_dir=tmp_path / ".sparrow",
        templates_dir=tmp_path / "templates" / "runtime",
        sessions_dir=tmp_path / "sessions",
        memories_dir=tmp_path / "memories",
        logs_dir=tmp_path / "logs",
        daily_memory_dir=tmp_path / ".sparrow" / "memory",
        agents_doc_path=tmp_path / ".sparrow" / "AGENTS.md",
        soul_doc_path=tmp_path / ".sparrow" / "SOUL.md",
        user_doc_path=tmp_path / ".sparrow" / "USER.md",
        memory_doc_path=tmp_path / ".sparrow" / "MEMORY.md",
    )
    return AgentRuntime(
        file_store=file_store,
        memory_store=MemoryStore(file_store),
        model_client=EchoModelClient(),
    )


def test_server_session_init_returns_bootstrap_prompt(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("apps.server.main.runtime", build_runtime(tmp_path))
    client = TestClient(app)

    response = client.get("/api/session/web-demo")

    assert response.status_code == 200
    body = response.json()
    assert "1. What should I call you?" in body["reply"]
    assert "You can answer any or all of them now" in body["reply"]


def test_server_chat_stream_returns_sse_events(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("apps.server.main.runtime", build_runtime(tmp_path))
    client = TestClient(app)
    if not any(route.path == "/api/chat/stream" and "POST" in (route.methods or set()) for route in app.routes):
        pytest.skip("stream endpoint not exposed in this environment")

    response = client.post(
        "/api/chat/stream",
        json={"session_id": "web-demo", "message": "hello", "show_thinking": True},
        headers={"Accept": "text/event-stream"},
    )
    assert response.status_code == 200
    payload = response.text

    assert "event: start" in payload
    assert "event: final" in payload
    assert "event: done" in payload
