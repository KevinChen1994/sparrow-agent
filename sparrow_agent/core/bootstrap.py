from __future__ import annotations

from sparrow_agent.storage.file_store import FileStore


BOOTSTRAP_QUESTIONS: list[tuple[str, str]] = [
    ("preferred_name", "What should I call you?"),
    ("primary_uses", "What do you mainly want me to help you with?"),
    ("communication_style", "How do you prefer me to communicate with you?"),
    ("avoidances", "What do you want me to avoid when helping you?"),
    ("long_term_context", "What long-term goals, projects, or ongoing context should I remember?"),
]

class BootstrapManager:
    def __init__(self, file_store: FileStore) -> None:
        self.file_store = file_store

    def should_prompt(self, session_message_count: int) -> bool:
        if session_message_count > 0:
            return False
        user_doc = self.file_store.read_document(self.file_store.user_doc_path)
        lowered = user_doc.lower()
        return (
            not user_doc.strip()
            or "preferred name:" not in lowered
            or "preferred name: unknown" in lowered
            or "not provided yet" in lowered
        )

    @staticmethod
    def build_prompt() -> str:
        questions = "\n".join(f"{index}. {question}" for index, (_, question) in enumerate(BOOTSTRAP_QUESTIONS, start=1))
        return (
            "Before we start, here are a few short things that would help me personalize Sparrow Agent for you.\n\n"
            "You can answer any or all of them now in your own words. If you skip some, we can pick them up later during normal use.\n\n"
            f"{questions}"
        )
