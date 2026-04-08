from __future__ import annotations

import re
from dataclasses import dataclass

from sparrow_agent.storage.file_store import FileStore


BOOTSTRAP_QUESTIONS: list[tuple[str, str]] = [
    ("name", "What should I call you?"),
    ("primary_uses", "What do you mainly want me to help you with?"),
    ("communication_style", "How do you prefer me to communicate with you?"),
    ("things_to_avoid", "What do you want me to avoid when helping you?"),
    ("long_term_context", "What long-term goals, projects, or ongoing context should I remember?"),
]

QUESTION_FIELD_MAP: dict[str, tuple[str, str]] = {
    "name": ("Profile", "Name"),
    "primary_uses": ("Stable Context", "Primary uses"),
    "communication_style": ("Preferences", "Communication style"),
    "things_to_avoid": ("Preferences", "Things to avoid"),
    "long_term_context": ("Stable Context", "Long-term context"),
}

QUESTION_TRANSLATIONS: dict[str, dict[str, str]] = {
    "english": {
        "name": "What should I call you?",
        "primary_uses": "What do you mainly want me to help you with?",
        "communication_style": "How do you prefer me to communicate with you?",
        "things_to_avoid": "What do you want me to avoid when helping you?",
        "long_term_context": "What long-term goals, projects, or ongoing context should I remember?",
        "intro": "Before we start, I want to learn a little about you so I can personalize Sparrow Agent.",
        "done": "Thanks. I have enough to get started.",
    },
    "chinese": {
        "name": "我应该怎么称呼你？",
        "primary_uses": "你主要希望我帮你做什么？",
        "communication_style": "你希望我用什么样的方式和你沟通？",
        "things_to_avoid": "我在帮助你时，有哪些事情是你希望我避免的？",
        "long_term_context": "有哪些长期目标、项目，或者持续性的背景信息是你希望我记住的？",
        "intro": "在开始之前，我想先简单了解你一点，这样我可以更好地个性化 Sparrow Agent。",
        "done": "好，我已经有足够的信息开始了。",
    },
    "japanese": {
        "name": "あなたを何とお呼びすればよいですか？",
        "primary_uses": "主にどんなことを私に手伝ってほしいですか？",
        "communication_style": "どのような話し方や伝え方を好みますか？",
        "things_to_avoid": "サポートする際に避けてほしいことはありますか？",
        "long_term_context": "覚えておいてほしい長期目標、プロジェクト、継続中の文脈はありますか？",
        "intro": "始める前に、あなたのことを少し知っておきたいです。そうすれば Sparrow Agent をよりあなた向けにできます。",
        "done": "ありがとうございます。始めるのに十分な情報がそろいました。",
    },
    "korean": {
        "name": "어떻게 불러드리면 될까요?",
        "primary_uses": "주로 어떤 일을 제가 도와드리면 될까요?",
        "communication_style": "어떤 방식으로 소통하길 원하시나요?",
        "things_to_avoid": "도와드릴 때 피했으면 하는 점이 있나요?",
        "long_term_context": "기억해 두길 원하는 장기 목표, 프로젝트, 또는 지속적인 맥락이 있나요?",
        "intro": "시작하기 전에, Sparrow Agent를 더 잘 맞추기 위해 당신에 대해 조금 알고 싶습니다.",
        "done": "감사합니다. 시작하기에 충분한 정보를 얻었습니다.",
    },
}

PLACEHOLDER_VALUES = {
    "",
    "not provided yet",
    "not provided yet.",
    "(your name)",
    "(preferred language)",
    "unknown",
}

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


@dataclass
class BootstrapReply:
    reply: str
    metadata: dict[str, object]
    completed: bool = False


def _split_lines(content: str) -> list[str]:
    return content.splitlines(keepends=True) if content else []


def _ensure_trailing_newline(text: str) -> str:
    return text if text.endswith("\n") else text + "\n"


def _find_heading_span(lines: list[str], heading: str) -> tuple[int, int, int, int]:
    target = heading.strip().lower()
    for index, line in enumerate(lines):
        match = HEADING_RE.match(line.strip("\n"))
        if not match:
            continue
        level = len(match.group(1))
        name = match.group(2).strip().lower()
        if name != target:
            continue
        body_start = index + 1
        end = len(lines)
        for probe in range(body_start, len(lines)):
            next_match = HEADING_RE.match(lines[probe].strip("\n"))
            if next_match and len(next_match.group(1)) <= level:
                end = probe
                break
        return index, body_start, end, level
    raise ValueError(f"Heading not found: {heading}")


def _section_parts(content: str, heading: str) -> tuple[list[str], list[str], list[str]]:
    lines = _split_lines(content)
    _, body_start, end, _ = _find_heading_span(lines, heading)
    prefix = lines[:body_start]
    body = lines[body_start:end]
    suffix = lines[end:]
    return prefix, body, suffix


def _join_parts(prefix: list[str], body: list[str], suffix: list[str]) -> str:
    return _ensure_trailing_newline("".join(prefix + body + suffix))


def _normalize_value(value: str) -> str:
    return " ".join(value.strip().split())


def _is_placeholder(value: str) -> bool:
    return _normalize_value(value).lower() in PLACEHOLDER_VALUES


def _contains_range(text: str, start: str, end: str) -> bool:
    return any(start <= char <= end for char in text)


def _infer_language(text: str) -> str | None:
    if _contains_range(text, "\u3040", "\u30ff"):
        return "Japanese"
    if _contains_range(text, "\uac00", "\ud7af"):
        return "Korean"
    if _contains_range(text, "\u4e00", "\u9fff"):
        return "Chinese"
    if _contains_range(text, "\u0400", "\u04ff"):
        return "Russian"
    if _contains_range(text, "\u0600", "\u06ff"):
        return "Arabic"
    if re.search(r"[A-Za-z]", text):
        return "English"
    return None


def _language_key(language: str | None) -> str:
    lowered = (language or "").strip().lower()
    alias_map = {
        "english": "english",
        "chinese": "chinese",
        "zh": "chinese",
        "zh-cn": "chinese",
        "japanese": "japanese",
        "ja": "japanese",
        "korean": "korean",
        "ko": "korean",
    }
    return alias_map.get(lowered, "english")


class BootstrapManager:
    def __init__(self, file_store: FileStore) -> None:
        self.file_store = file_store

    def should_prompt(self, session_message_count: int) -> bool:
        if session_message_count > 0:
            return False
        return self.answered_question_count() == 0

    def build_prompt(self, language: str | None = None) -> BootstrapReply:
        return self._build_question_reply(
            question_key=BOOTSTRAP_QUESTIONS[0][0],
            question_number=1,
            language=language,
            include_intro=True,
        )

    def is_waiting_for_answer(self, messages: list) -> bool:
        if not messages:
            return False
        last_message = messages[-1]
        return last_message.role == "assistant" and bool(last_message.metadata.get("bootstrap"))

    def handle_answer(self, question_key: str, answer: str) -> BootstrapReply:
        cleaned_answer = _normalize_value(answer)
        if not cleaned_answer:
            return self._build_question_reply(
                question_key=question_key,
                question_number=self._question_number(question_key),
                language=self.current_language(),
            )

        self._update_user_answer(question_key=question_key, answer=cleaned_answer)
        detected_language = _infer_language(answer)
        if detected_language is not None:
            self._update_user_field("Profile", "Language", detected_language)

        self._append_daily_memory(question_key=question_key, answer=cleaned_answer)
        if question_key == "long_term_context":
            self._upsert_memory_ongoing_context(cleaned_answer)

        next_question_key = self.next_unanswered_question()
        if next_question_key is None:
            prompt_map = QUESTION_TRANSLATIONS[_language_key(self.current_language())]
            return BootstrapReply(reply=prompt_map["done"], metadata={"bootstrap": False}, completed=True)

        return self._build_question_reply(
            question_key=next_question_key,
            question_number=self._question_number(next_question_key),
            language=self.current_language(),
        )

    def answered_question_count(self) -> int:
        user_doc = self.file_store.read_document(self.file_store.user_doc_path)
        count = 0
        for heading, key in QUESTION_FIELD_MAP.values():
            value = self._read_user_field(user_doc, heading, key)
            if not _is_placeholder(value):
                count += 1
        return count

    def next_unanswered_question(self) -> str | None:
        user_doc = self.file_store.read_document(self.file_store.user_doc_path)
        for question_key, (heading, key) in QUESTION_FIELD_MAP.items():
            value = self._read_user_field(user_doc, heading, key)
            if _is_placeholder(value):
                return question_key
        return None

    def current_language(self) -> str | None:
        user_doc = self.file_store.read_document(self.file_store.user_doc_path)
        language = self._read_user_field(user_doc, "Profile", "Language")
        return None if _is_placeholder(language) else language

    def _question_number(self, question_key: str) -> int:
        for index, (candidate, _) in enumerate(BOOTSTRAP_QUESTIONS, start=1):
            if candidate == question_key:
                return index
        raise ValueError(f"Unknown bootstrap question key: {question_key}")

    def _build_question_reply(
        self,
        question_key: str,
        question_number: int,
        language: str | None,
        include_intro: bool = False,
    ) -> BootstrapReply:
        prompt_map = QUESTION_TRANSLATIONS[_language_key(language)]
        lines = [f"{question_number}/5. {prompt_map[question_key]}"]
        if include_intro:
            lines.insert(0, prompt_map["intro"])
        return BootstrapReply(
            reply="\n\n".join(lines),
            metadata={
                "bootstrap": True,
                "bootstrap_key": question_key,
                "bootstrap_question_number": question_number,
            },
        )

    def _read_user_field(self, content: str, heading: str, key: str) -> str:
        try:
            _, body, _ = _section_parts(content, heading)
        except ValueError:
            return ""
        prefix = f"- {key}:"
        for line in body:
            stripped = line.strip()
            if stripped.startswith(prefix):
                return stripped.removeprefix(prefix).strip()
        return ""

    def _update_user_answer(self, question_key: str, answer: str) -> None:
        heading, key = QUESTION_FIELD_MAP[question_key]
        self._update_user_field(heading, key, answer)

    def _update_user_field(self, heading: str, key: str, value: str) -> None:
        path = self.file_store.user_doc_path
        content = self.file_store.read_document(path)
        try:
            prefix, body, suffix = _section_parts(content, heading)
        except ValueError:
            return

        new_line = f"- {key}: {value}\n"
        line_prefix = f"- {key}:"
        replaced = False
        for index, line in enumerate(body):
            if line.strip().startswith(line_prefix):
                body[index] = new_line
                replaced = True
                break
        if not replaced:
            body.append(new_line)
        self.file_store.write_document(path, _join_parts(prefix, body, suffix))

    def _append_daily_memory(self, question_key: str, answer: str) -> None:
        path = self.file_store.get_daily_memory_path()
        if not path.exists():
            self.file_store.write_document(path, "# Daily Memory\n\n## Summary\n")
        self.file_store.append_document(path, f"\n- Bootstrap {question_key.replace('_', ' ')}: {answer}\n")

    def _upsert_memory_ongoing_context(self, value: str) -> None:
        path = self.file_store.memory_doc_path
        content = self.file_store.read_document(path)
        try:
            prefix, body, suffix = _section_parts(content, "Ongoing Context")
        except ValueError:
            return

        body = [line for line in body if line.strip() != "- No ongoing context captured yet."]
        bullet = f"- {value}\n"
        if bullet not in body:
            body.append(bullet)
        if not body:
            body = ["- No ongoing context captured yet.\n"]
        self.file_store.write_document(path, _join_parts(prefix, body, suffix))
