from __future__ import annotations

from pathlib import Path

from sparrow_agent.schemas.models import RuntimeContext, ToolDefinition, ToolResult
from sparrow_agent.storage.file_store import FileStore


def _append_section(existing: str, heading: str, body: str) -> str:
    if not body.strip():
        return existing
    snippet = f"\n## {heading}\n{body.strip()}\n"
    if f"## {heading}\n" in existing:
        return existing.rstrip() + "\n" + body.strip() + "\n"
    return existing.rstrip() + snippet


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


class UpdateMarkdownDocTool:
    def __init__(self, file_store: FileStore, name: str, path: Path, heading: str, description: str, requires_confirmation: bool = False) -> None:
        self.file_store = file_store
        self.name = name
        self.path = path
        self.heading = heading
        self.description_text = description
        self.requires_confirmation = requires_confirmation

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description_text,
            input_schema={"type": "object", "properties": {"content": {"type": "string"}}, "required": ["content"]},
            side_effect_profile="write",
            mutates_memory=True,
            requires_confirmation=self.requires_confirmation,
        )

    def execute(self, input_data: dict, ctx: RuntimeContext) -> ToolResult:
        del ctx
        content = str(input_data.get("content", "")).strip()
        existing = self.file_store.read_document(self.path)
        if self.requires_confirmation:
            proposal = f"# Proposed Update\n\n## {self.heading}\n{content}\n"
            proposal_path = self.path.with_suffix(".proposal.md")
            self.file_store.write_document(proposal_path, proposal)
            return ToolResult(content=f"Proposed update at {proposal_path}", metadata={"path": str(proposal_path)})

        updated = _append_section(existing or f"# {self.heading}\n", self.heading, f"- {content}")
        self.file_store.write_document(self.path, updated)
        return ToolResult(content=f"Updated {self.path}", metadata={"path": str(self.path)})


def build_memory_tools(file_store: FileStore) -> list:
    return [
        AppendDailyMemoryTool(file_store),
        UpdateMarkdownDocTool(
            file_store=file_store,
            name="update_user_doc",
            path=file_store.user_doc_path,
            heading="Preferences",
            description="Add stable user profile or preference information to USER.md.",
        ),
        UpdateMarkdownDocTool(
            file_store=file_store,
            name="update_memory_doc",
            path=file_store.memory_doc_path,
            heading="Important Notes",
            description="Add long-term reusable context to MEMORY.md.",
        ),
        UpdateMarkdownDocTool(
            file_store=file_store,
            name="propose_soul_patch",
            path=file_store.soul_doc_path,
            heading="Style",
            description="Propose a modification to SOUL.md for later review.",
            requires_confirmation=True,
        ),
        UpdateMarkdownDocTool(
            file_store=file_store,
            name="propose_agents_patch",
            path=file_store.agents_doc_path,
            heading="Identity",
            description="Propose a modification to AGENTS.md for later review.",
            requires_confirmation=True,
        ),
    ]
