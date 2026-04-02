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

    tools["update_user_doc"].execute({"content": "User prefers bullet lists."}, ctx)
    tools["update_memory_doc"].execute({"content": "Sparrow Agent uses markdown memory."}, ctx)
    tools["append_daily_memory"].execute({"content": "Discussed architecture."}, ctx)
    result = tools["propose_soul_patch"].execute({"content": "Prefer direct conclusions first."}, ctx)

    assert "bullet lists" in store.read_document(store.user_doc_path)
    assert "markdown memory" in store.read_document(store.memory_doc_path)
    assert "Discussed architecture." in store.read_document(store.get_daily_memory_path())
    assert result.metadata["path"].endswith(".proposal.md")
