from __future__ import annotations

import re
from pathlib import Path

from sparrow_agent.schemas.models import RuntimeContext, ToolDefinition, ToolResult
from sparrow_agent.storage.file_store import FileStore


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def _split_lines(content: str) -> list[str]:
    if not content:
        return []
    return content.splitlines(keepends=True)


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
    merged = "".join(prefix + body + suffix)
    return _ensure_trailing_newline(merged)


def _parse_bullet_key_value(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped.startswith("- "):
        return None
    raw = stripped[2:]
    if ":" not in raw:
        return None
    key, value = raw.split(":", 1)
    return key.strip(), value.strip()


class AppendDailyMemoryTool:
    def __init__(self, file_store: FileStore) -> None:
        self.file_store = file_store

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="append_daily_memory",
            description="Append a summary or decision to today's daily memory markdown file.",
            input_schema={
                "type": "object",
                "properties": {"content": {"type": "string"}, "day": {"type": "string"}},
                "required": ["content"],
            },
            side_effect_profile="write",
            mutates_memory=True,
        )

    def execute(self, input_data: dict, ctx: RuntimeContext) -> ToolResult:
        del ctx
        path = self.file_store.get_daily_memory_path(input_data.get("day"))
        content = str(input_data.get("content", "")).strip()
        if not path.exists():
            self.file_store.write_document(path, "# Daily Memory\n\n## Summary\n")
        self.file_store.append_document(path, f"\n- {content}\n")
        return ToolResult(content=f"Updated {path}", metadata={"path": str(path)})


class PatchMemoryDocTool:
    def __init__(self, file_store: FileStore) -> None:
        self.file_store = file_store

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="patch_memory_doc",
            description=(
                "Patch USER.md or MEMORY.md by heading with structured operations. "
                "Supports key-value and keyless sentence updates."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "document": {"type": "string", "enum": ["user", "memory"]},
                    "operation": {
                        "type": "string",
                        "enum": ["upsert_kv", "upsert_bullet", "insert_after_heading", "replace_span", "delete_span"],
                    },
                    "heading": {"type": "string"},
                    "key": {"type": "string"},
                    "value": {"type": "string"},
                    "text": {"type": "string"},
                    "old_text": {"type": "string"},
                    "new_text": {"type": "string"},
                },
                "required": ["document", "operation", "heading"],
            },
            side_effect_profile="write",
            mutates_memory=True,
        )

    def execute(self, input_data: dict, ctx: RuntimeContext) -> ToolResult:
        del ctx
        document = str(input_data.get("document", "")).strip().lower()
        operation = str(input_data.get("operation", "")).strip().lower()
        heading = str(input_data.get("heading", "")).strip()

        if not heading:
            return ToolResult(content="Error: heading is required.")

        if document == "user":
            path = self.file_store.user_doc_path
        elif document == "memory":
            path = self.file_store.memory_doc_path
        else:
            return ToolResult(content=f"Error: unsupported document: {document}")

        content = self.file_store.read_document(path)
        try:
            prefix, body, suffix = _section_parts(content, heading)
        except ValueError as exc:
            return ToolResult(content=f"Error: {exc}")

        changed = False
        body_text = "".join(body)

        if operation == "upsert_kv":
            key = str(input_data.get("key", "")).strip()
            value = str(input_data.get("value", "")).strip()
            if not key or not value:
                return ToolResult(content="Error: upsert_kv requires key and value.")

            new_line = f"- {key}: {value}\n"
            matches: list[int] = []
            for idx, line in enumerate(body):
                parsed = _parse_bullet_key_value(line)
                if parsed and parsed[0].lower() == key.lower():
                    matches.append(idx)

            if matches:
                first = matches[0]
                if body[first] != new_line:
                    body[first] = new_line
                    changed = True
                for idx in reversed(matches[1:]):
                    body.pop(idx)
                    changed = True
            else:
                body.append(new_line)
                changed = True

        elif operation == "upsert_bullet":
            value = str(input_data.get("value", "")).strip()
            if not value:
                return ToolResult(content="Error: upsert_bullet requires value.")
            target = f"- {value}"
            found = any(line.strip() == target for line in body)
            if not found:
                body.append(target + "\n")
                changed = True

        elif operation == "insert_after_heading":
            text = str(input_data.get("text", "")).strip()
            if not text:
                return ToolResult(content="Error: insert_after_heading requires text.")
            body.insert(0, _ensure_trailing_newline(text))
            changed = True

        elif operation == "replace_span":
            old_text = str(input_data.get("old_text", ""))
            new_text = str(input_data.get("new_text", ""))
            if not old_text:
                return ToolResult(content="Error: replace_span requires old_text.")
            count = body_text.count(old_text)
            if count == 0:
                return ToolResult(content="Error: old_text not found in heading body.")
            if count > 1:
                return ToolResult(content="Error: old_text appears multiple times in heading body.")
            body_text = body_text.replace(old_text, new_text, 1)
            body = _split_lines(body_text)
            changed = True

        elif operation == "delete_span":
            text = str(input_data.get("text", ""))
            if not text:
                return ToolResult(content="Error: delete_span requires text.")
            count = body_text.count(text)
            if count == 0:
                return ToolResult(content="Error: text not found in heading body.")
            if count > 1:
                return ToolResult(content="Error: text appears multiple times in heading body.")
            body_text = body_text.replace(text, "", 1)
            body = _split_lines(body_text)
            changed = True

        else:
            return ToolResult(content=f"Error: unsupported operation: {operation}")

        if not changed:
            return ToolResult(content=f"No changes for {path}", metadata={"path": str(path), "changed": False})

        updated = _join_parts(prefix, body, suffix)
        self.file_store.write_document(path, updated)
        return ToolResult(
            content=f"Patched {path} with {operation}",
            metadata={"path": str(path), "changed": True, "operation": operation, "heading": heading},
        )


class ProposeSoulPatchTool:
    def __init__(self, file_store: FileStore) -> None:
        self.file_store = file_store

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="propose_soul_patch",
            description="Propose a modification to SOUL.md for later review.",
            input_schema={"type": "object", "properties": {"content": {"type": "string"}}, "required": ["content"]},
            side_effect_profile="write",
            mutates_memory=True,
            requires_confirmation=True,
        )

    def execute(self, input_data: dict, ctx: RuntimeContext) -> ToolResult:
        del ctx
        content = str(input_data.get("content", "")).strip()
        proposal = f"# Proposed Update\n\n## Style\n{content}\n"
        proposal_path = self.file_store.soul_doc_path.with_suffix(".proposal.md")
        self.file_store.write_document(proposal_path, proposal)
        return ToolResult(content=f"Proposed update at {proposal_path}", metadata={"path": str(proposal_path)})


def build_memory_tools(file_store: FileStore) -> list:
    return [
        AppendDailyMemoryTool(file_store),
        PatchMemoryDocTool(file_store=file_store),
        ProposeSoulPatchTool(file_store=file_store),
    ]
