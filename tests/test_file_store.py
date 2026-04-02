from __future__ import annotations

from pathlib import Path

from sparrow_agent.schemas.models import MemoryItem, SessionRecord
from sparrow_agent.storage.file_store import FileStore


def create_runtime_templates(tmp_path: Path) -> None:
    template_dir = tmp_path / "templates" / "runtime"
    (template_dir / "memory").mkdir(parents=True, exist_ok=True)
    (template_dir / "AGENTS.md").write_text("# Template AGENTS\n", encoding="utf-8")
    (template_dir / "SOUL.md").write_text("# Template SOUL\n", encoding="utf-8")
    (template_dir / "USER.md").write_text("# Template USER\n", encoding="utf-8")
    (template_dir / "MEMORY.md").write_text("# Template MEMORY\n", encoding="utf-8")


def build_store(tmp_path: Path) -> FileStore:
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


def test_session_round_trip(tmp_path: Path) -> None:
    store = build_store(tmp_path)
    record = SessionRecord(session_id="demo")
    store.save_session(record)

    loaded = store.load_session("demo")
    assert loaded.session_id == "demo"
    assert loaded.messages == []


def test_memory_recall_matches_query(tmp_path: Path) -> None:
    store = build_store(tmp_path)
    store.append_memory(MemoryItem(text="User prefers Python and file storage"))
    store.append_memory(MemoryItem(text="User likes Rust for tooling"))

    recalled = store.recall_memories("Python", limit=5)
    assert len(recalled) == 1
    assert recalled[0].text == "User prefers Python and file storage"


def test_ensure_core_documents(tmp_path: Path) -> None:
    store = build_store(tmp_path)

    store.ensure_core_documents()

    assert (tmp_path / ".sparrow" / "AGENTS.md").exists()
    assert (tmp_path / ".sparrow" / "SOUL.md").exists()
    assert (tmp_path / ".sparrow" / "USER.md").exists()
    assert (tmp_path / ".sparrow" / "MEMORY.md").exists()
    assert (tmp_path / ".sparrow" / "AGENTS.md").read_text(encoding="utf-8") == "# Template AGENTS\n"
