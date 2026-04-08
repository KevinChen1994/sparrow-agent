from __future__ import annotations

from sparrow_agent.core.context_loader import ContextLoader
from sparrow_agent.storage.file_store import FileStore


def create_runtime_templates(tmp_path) -> None:
    template_dir = tmp_path / "templates" / "runtime"
    (template_dir / "memory").mkdir(parents=True, exist_ok=True)
    (template_dir / "AGENTS.md").write_text("# Template AGENTS\n", encoding="utf-8")
    (template_dir / "SOUL.md").write_text("# Template SOUL\n", encoding="utf-8")
    (template_dir / "USER.md").write_text("# Template USER\n", encoding="utf-8")
    (template_dir / "MEMORY.md").write_text("# Template MEMORY\n", encoding="utf-8")
    (template_dir / "memory" / "README.md").write_text("# Template Daily Memory\n", encoding="utf-8")


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


def test_context_loader_creates_core_docs_and_daily_memory(tmp_path) -> None:
    store = build_store(tmp_path)
    loader = ContextLoader(store)

    loaded = loader.load()

    kinds = [document.kind for document in loaded.documents]
    assert kinds[:4] == ["agents", "soul", "user", "memory"]
    assert "daily" in kinds
    assert (tmp_path / ".sparrow" / "memory").exists()
    assert (tmp_path / ".sparrow" / "AGENTS.md").read_text(encoding="utf-8") == "# Template AGENTS\n"
