from __future__ import annotations

from sparrow_agent.schemas.models import MemoryItem
from sparrow_agent.storage.file_store import FileStore


class MemoryStore:
    def __init__(self, file_store: FileStore) -> None:
        self.file_store = file_store

    def recall(self, query: str, session_id: str, limit: int = 5) -> list[MemoryItem]:
        del session_id
        return self.file_store.recall_memories(query=query, limit=limit)

    def save_fact(self, text: str, source: str = "assistant", tags: list[str] | None = None) -> MemoryItem:
        item = MemoryItem(text=text, source=source, tags=tags or [])
        self.file_store.append_memory(item)
        return item
