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
        sessions_dir=tmp_path / ".sparrow" / "sessions",
        logs_dir=tmp_path / ".sparrow" / "logs",
        daily_memory_dir=tmp_path / ".sparrow" / "memory",
        agents_doc_path=tmp_path / ".sparrow" / "AGENTS.md",
        soul_doc_path=tmp_path / ".sparrow" / "SOUL.md",
        user_doc_path=tmp_path / ".sparrow" / "USER.md",
        memory_doc_path=tmp_path / ".sparrow" / "MEMORY.md",
    )


def test_memory_tools_update_markdown_docs(tmp_path) -> None:
    store = build_store(tmp_path)
    store.ensure_core_documents()
    store.write_document(
        store.user_doc_path,
        (
            "# USER\n\n"
            "## Profile\n"
            "- Preferred name: Unknown\n"
            "- Language: Chinese\n\n"
            "## Preferences\n"
            "- Communication style: Concise and direct\n\n"
            "## Current Priorities\n"
            "- Primary uses: Not provided yet.\n"
        ),
    )
    store.write_document(
        store.memory_doc_path,
        (
            "# MEMORY\n\n"
            "## Long-Term Facts\n"
            "- No long-term facts captured yet.\n\n"
            "## Ongoing Context\n"
            "- No ongoing context captured yet.\n\n"
            "## Working Notes\n"
            "- No reusable working notes captured yet.\n"
        ),
    )
    tools = {tool.definition().name: tool for tool in build_memory_tools(store)}
    ctx = RuntimeContext(session_id="demo", user_input="hello", messages=[], active_skills=[], loop_state=LoopState())

    tools["patch_memory_doc"].execute(
        {
            "document": "user",
            "operation": "upsert_kv",
            "heading": "Profile",
            "key": "Preferred name",
            "value": "Meng",
        },
        ctx,
    )
    tools["patch_memory_doc"].execute(
        {
            "document": "memory",
            "operation": "upsert_bullet",
            "heading": "Long-Term Facts",
            "value": "Sparrow Agent uses markdown memory.",
        },
        ctx,
    )
    tools["patch_memory_doc"].execute(
        {
            "document": "memory",
            "operation": "insert_after_heading",
            "heading": "Working Notes",
            "text": "A freeform memory sentence without key.",
        },
        ctx,
    )
    tools["append_daily_memory"].execute({"content": "Discussed architecture."}, ctx)
    result = tools["propose_soul_patch"].execute({"content": "Prefer direct conclusions first."}, ctx)

    user_doc = store.read_document(store.user_doc_path)
    memory_doc = store.read_document(store.memory_doc_path)
    assert "- Preferred name: Meng" in user_doc
    assert user_doc.count("Preferred name:") == 1
    assert "markdown memory" in store.read_document(store.memory_doc_path)
    assert "A freeform memory sentence without key." in memory_doc
    assert "Discussed architecture." in store.read_document(store.get_daily_memory_path())
    assert result.metadata["path"].endswith(".proposal.md")
