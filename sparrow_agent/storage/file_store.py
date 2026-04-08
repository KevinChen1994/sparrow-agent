from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from sparrow_agent.config import (
    AGENTS_DOC_PATH,
    DAILY_MEMORY_DIR,
    DEFAULT_AGENTS_DOC,
    DEFAULT_MEMORY_DOC,
    DEFAULT_SOUL_DOC,
    DEFAULT_USER_DOC,
    LOGS_DIR,
    MEMORY_DOC_PATH,
    RUNTIME_DIR,
    RUNTIME_TEMPLATES_DIR,
    SESSIONS_DIR,
    SOUL_DOC_PATH,
    USER_DOC_PATH,
    WORKSPACE_ROOT,
    ensure_data_dirs,
)
from sparrow_agent.schemas.models import DocumentSnapshot, Message, SessionRecord


class FileStore:
    def __init__(
        self,
        sessions_dir: Path = SESSIONS_DIR,
        logs_dir: Path = LOGS_DIR,
        workspace_root: Path = WORKSPACE_ROOT,
        runtime_dir: Path = RUNTIME_DIR,
        templates_dir: Path = RUNTIME_TEMPLATES_DIR,
        daily_memory_dir: Path = DAILY_MEMORY_DIR,
        agents_doc_path: Path = AGENTS_DOC_PATH,
        soul_doc_path: Path = SOUL_DOC_PATH,
        user_doc_path: Path = USER_DOC_PATH,
        memory_doc_path: Path = MEMORY_DOC_PATH,
    ) -> None:
        ensure_data_dirs()
        self.sessions_dir = sessions_dir
        self.logs_dir = logs_dir
        self.workspace_root = workspace_root
        self.runtime_dir = runtime_dir
        self.templates_dir = templates_dir
        self.daily_memory_dir = daily_memory_dir
        self.agents_doc_path = agents_doc_path
        self.soul_doc_path = soul_doc_path
        self.user_doc_path = user_doc_path
        self.memory_doc_path = memory_doc_path
        for path in (self.sessions_dir, self.logs_dir, self.runtime_dir, self.daily_memory_dir):
            path.mkdir(parents=True, exist_ok=True)

    def load_session(self, session_id: str) -> SessionRecord:
        path = self.sessions_dir / f"{session_id}.json"
        if not path.exists():
            return SessionRecord(session_id=session_id)
        return SessionRecord.model_validate_json(path.read_text(encoding="utf-8"))

    def save_session(self, record: SessionRecord) -> None:
        record.updated_at = datetime.now(timezone.utc)
        path = self.sessions_dir / f"{record.session_id}.json"
        path.write_text(record.model_dump_json(indent=2), encoding="utf-8")

    def append_log(self, payload: dict) -> None:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path = self.logs_dir / f"{today}.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False))
            handle.write("\n")

    def ensure_core_documents(self) -> None:
        self._sync_runtime_templates()
        defaults = {
            self.agents_doc_path: DEFAULT_AGENTS_DOC,
            self.soul_doc_path: DEFAULT_SOUL_DOC,
            self.user_doc_path: DEFAULT_USER_DOC,
            self.memory_doc_path: DEFAULT_MEMORY_DOC,
        }
        for path, content in defaults.items():
            if not path.exists():
                path.write_text(content, encoding="utf-8")

    def _sync_runtime_templates(self) -> None:
        if not self.templates_dir.exists():
            return
        for item in sorted(self.templates_dir.rglob("*")):
            relative = item.relative_to(self.templates_dir)
            destination = self.runtime_dir / relative
            if item.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
                continue
            if destination.exists():
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(item.read_text(encoding="utf-8"), encoding="utf-8")

    def read_document(self, path: Path) -> str:
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def write_document(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def append_document(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(content)

    def replace_document_text(self, path: Path, old_text: str, new_text: str) -> bool:
        content = self.read_document(path)
        if old_text not in content:
            return False
        self.write_document(path, content.replace(old_text, new_text, 1))
        return True

    def snapshot_document(self, kind: str, path: Path) -> DocumentSnapshot:
        updated_at = None
        if path.exists():
            updated_at = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
        return DocumentSnapshot(kind=kind, path=str(path), content=self.read_document(path), updated_at=updated_at)

    def get_daily_memory_path(self, day: str | None = None) -> Path:
        day = day or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self.daily_memory_dir / f"{day}.md"

    def list_recent_daily_memory_paths(self, limit: int = 2) -> list[Path]:
        paths = sorted(self.daily_memory_dir.glob("*.md"))
        return paths[-limit:]

    def trim_session_messages(self, record: SessionRecord, keep_from_index: int, tool_result_max_chars: int) -> SessionRecord:
        if keep_from_index <= 0:
            return record
        record.last_consolidated_index = max(record.last_consolidated_index, keep_from_index)
        record.messages = [self._truncate_tool_message(message, tool_result_max_chars) for message in record.messages[keep_from_index:]]
        return record

    @staticmethod
    def _truncate_tool_message(message: Message, tool_result_max_chars: int) -> Message:
        if message.role != "tool" or len(message.content) <= tool_result_max_chars:
            return message
        truncated = message.content[:tool_result_max_chars] + "\n... (truncated)"
        return message.model_copy(update={"content": truncated})
