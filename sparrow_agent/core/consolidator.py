from __future__ import annotations

from sparrow_agent.schemas.models import ConsolidationResult, Message, SessionRecord
from sparrow_agent.storage.file_store import FileStore


class SessionConsolidator:
    def __init__(self, file_store: FileStore, memory_window: int = 100, tool_result_max_chars: int = 500) -> None:
        self.file_store = file_store
        self.memory_window = memory_window
        self.tool_result_max_chars = tool_result_max_chars

    def maybe_consolidate(self, session: SessionRecord) -> ConsolidationResult:
        unconsolidated = len(session.messages) - session.last_consolidated_index
        if unconsolidated < self.memory_window:
            return ConsolidationResult(triggered=False)

        end_index = max(session.last_consolidated_index + 1, len(session.messages) - (self.memory_window // 2))
        chunk = session.messages[session.last_consolidated_index:end_index]
        summary = self._summarize_chunk(chunk)
        if summary:
            daily_path = self.file_store.get_daily_memory_path()
            if not daily_path.exists():
                self.file_store.write_document(daily_path, "# Daily Memory\n\n## Summary\n")
            self.file_store.append_document(daily_path, f"\n- Consolidated session history: {summary}\n")

            memory_content = self.file_store.read_document(self.file_store.memory_doc_path)
            if summary not in memory_content:
                updated = memory_content.rstrip() + f"\n- {summary}\n"
                self.file_store.write_document(self.file_store.memory_doc_path, updated)

        self.file_store.trim_session_messages(session, keep_from_index=end_index, tool_result_max_chars=self.tool_result_max_chars)
        return ConsolidationResult(
            triggered=True,
            reason="memory_window",
            daily_summary=summary,
            memory_update=summary,
            new_last_consolidated_index=session.last_consolidated_index,
        )

    @staticmethod
    def _summarize_chunk(messages: list[Message]) -> str:
        parts: list[str] = []
        for message in messages:
            if not message.content.strip():
                continue
            prefix = message.role.upper()
            parts.append(f"{prefix}: {message.content.strip()[:120]}")
            if len(parts) >= 6:
                break
        return " | ".join(parts)
