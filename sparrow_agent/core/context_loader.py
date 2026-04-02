from __future__ import annotations

from dataclasses import dataclass

from sparrow_agent.storage.file_store import FileStore


@dataclass
class LoadedContext:
    documents: list


class ContextLoader:
    def __init__(self, file_store: FileStore, recent_daily_limit: int = 2) -> None:
        self.file_store = file_store
        self.recent_daily_limit = recent_daily_limit

    def load(self) -> LoadedContext:
        self.file_store.ensure_core_documents()
        daily_path = self.file_store.get_daily_memory_path()
        if not daily_path.exists():
            self.file_store.write_document(daily_path, "# Daily Memory\n\n## Summary\n")

        documents = [
            self.file_store.snapshot_document("agents", self.file_store.agents_doc_path),
            self.file_store.snapshot_document("soul", self.file_store.soul_doc_path),
            self.file_store.snapshot_document("user", self.file_store.user_doc_path),
            self.file_store.snapshot_document("memory", self.file_store.memory_doc_path),
        ]
        for path in self.file_store.list_recent_daily_memory_paths(limit=self.recent_daily_limit):
            documents.append(self.file_store.snapshot_document("daily", path))

        return LoadedContext(documents=documents)
