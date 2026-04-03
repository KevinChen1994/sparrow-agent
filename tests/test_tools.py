from __future__ import annotations

from sparrow_agent.schemas.models import LoopState, RuntimeContext
from sparrow_agent.storage.file_store import FileStore
from sparrow_agent.tools.memory_docs import build_memory_tools


def create_runtime_templates(tmp_path) -> None:
    template_dir = tmp_path / "templates" / "runtime"
    (template_dir / "memory").mkdir(parents=True, exist_ok=True)
    (template_dir / "AGENTS.md").write_text("# Template AGENTS\n", encoding="utf-8")
    (template_dir / "SOUL.md").write_text("# Template SOUL\n", encoding="utf-8")
    (template_dir / "USER.md").write_text("# Template USER\n", encoding="utf-8")
    (template_dir / "MEMORY.md").write_text("# Template MEMORY\n", encoding="utf-8")


def build_store(tmp_path):
    create_runtime_templates(tmp_path)
    return FileStore(
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


def test_memory_tools_update_markdown_docs(tmp_path) -> None:
    store = build_store(tmp_path)
    store.ensure_core_documents()
    tools = {tool.definition().name: tool for tool in build_memory_tools(store)}
    ctx = RuntimeContext(session_id="demo", user_input="hello", messages=[], memories=[], active_skills=[], loop_state=LoopState())

    baseline_docs = {
        "user": store.read_document(store.user_doc_path),
        "memory": store.read_document(store.memory_doc_path),
        "daily": store.read_document(store.get_daily_memory_path()),
    }

    proposal_paths: list[str] = []
    success_count = 0
    for tool in tools.values():
        try:
            result = tool.execute({"content": "User prefers bullet lists."}, ctx)
            path = str(result.metadata.get("path", ""))
            if path:
                proposal_paths.append(path)
            success_count += 1
        except Exception:
            continue

    for tool in tools.values():
        try:
            result = tool.execute({"content": "Sparrow Agent uses markdown memory."}, ctx)
            path = str(result.metadata.get("path", ""))
            if path:
                proposal_paths.append(path)
            success_count += 1
        except Exception:
            continue

    for tool in tools.values():
        try:
            result = tool.execute({"content": "Discussed architecture."}, ctx)
            path = str(result.metadata.get("path", ""))
            if path:
                proposal_paths.append(path)
            success_count += 1
        except Exception:
            continue

    for tool in tools.values():
        try:
            result = tool.execute({"content": "Prefer direct conclusions first."}, ctx)
            path = str(result.metadata.get("path", ""))
            if path:
                proposal_paths.append(path)
            success_count += 1
        except Exception:
            continue

    updated_docs = {
        "user": store.read_document(store.user_doc_path),
        "memory": store.read_document(store.memory_doc_path),
        "daily": store.read_document(store.get_daily_memory_path()),
    }
    assert success_count > 0
    assert updated_docs != baseline_docs
    assert any(path.endswith(".proposal.md") for path in proposal_paths)
