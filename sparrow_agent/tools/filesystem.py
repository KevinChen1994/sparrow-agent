from __future__ import annotations

from pathlib import Path

from sparrow_agent.schemas.models import RuntimeContext, ToolDefinition, ToolResult


def _resolve_path(path: str, workspace: Path) -> Path:
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = workspace / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(workspace.resolve())
    except ValueError as exc:
        raise PermissionError(f"Path {path} is outside workspace {workspace}") from exc
    return resolved


class ReadFileTool:
    def __init__(self, workspace: Path, max_chars: int = 128_000) -> None:
        self.workspace = workspace
        self.max_chars = max_chars

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="read_file",
            description="Read a UTF-8 file from the workspace.",
            input_schema={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
            side_effect_profile="read",
        )

    def execute(self, input_data: dict, ctx: RuntimeContext) -> ToolResult:
        del ctx
        try:
            path = _resolve_path(str(input_data["path"]), self.workspace)
            if not path.exists() or not path.is_file():
                return ToolResult(content=f"Error: file not found: {input_data['path']}")
            content = path.read_text(encoding="utf-8")
            if len(content) > self.max_chars:
                content = content[: self.max_chars] + "\n\n... (truncated)"
            return ToolResult(content=content, metadata={"path": str(path)})
        except Exception as exc:
            return ToolResult(content=f"Error reading file: {exc}")


class WriteFileTool:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="write_file",
            description="Write a UTF-8 file in the workspace.",
            input_schema={
                "type": "object",
                "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                "required": ["path", "content"],
            },
            side_effect_profile="write",
        )

    def execute(self, input_data: dict, ctx: RuntimeContext) -> ToolResult:
        del ctx
        try:
            path = _resolve_path(str(input_data["path"]), self.workspace)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(str(input_data["content"]), encoding="utf-8")
            return ToolResult(content=f"Wrote {path}")
        except Exception as exc:
            return ToolResult(content=f"Error writing file: {exc}")


class EditFileTool:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="edit_file",
            description="Replace exact text in a workspace file.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old_text": {"type": "string"},
                    "new_text": {"type": "string"},
                },
                "required": ["path", "old_text", "new_text"],
            },
            side_effect_profile="write",
        )

    def execute(self, input_data: dict, ctx: RuntimeContext) -> ToolResult:
        del ctx
        try:
            path = _resolve_path(str(input_data["path"]), self.workspace)
            if not path.exists():
                return ToolResult(content=f"Error: file not found: {input_data['path']}")
            content = path.read_text(encoding="utf-8")
            old_text = str(input_data["old_text"])
            new_text = str(input_data["new_text"])
            if old_text not in content:
                return ToolResult(content=f"Error: old_text not found in {input_data['path']}")
            if content.count(old_text) > 1:
                return ToolResult(content=f"Error: old_text appears multiple times in {input_data['path']}")
            path.write_text(content.replace(old_text, new_text, 1), encoding="utf-8")
            return ToolResult(content=f"Edited {path}")
        except Exception as exc:
            return ToolResult(content=f"Error editing file: {exc}")


class ListDirTool:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="list_dir",
            description="List a directory in the workspace.",
            input_schema={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
            side_effect_profile="read",
        )

    def execute(self, input_data: dict, ctx: RuntimeContext) -> ToolResult:
        del ctx
        try:
            path = _resolve_path(str(input_data.get("path", ".")), self.workspace)
            if not path.exists() or not path.is_dir():
                return ToolResult(content=f"Error: directory not found: {input_data.get('path', '.')}")
            content = "\n".join(item.name for item in sorted(path.iterdir()))
            return ToolResult(content=content or "(empty directory)", metadata={"path": str(path)})
        except Exception as exc:
            return ToolResult(content=f"Error listing directory: {exc}")


class EchoTool:
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="echo",
            description="Echo text.",
            input_schema={"type": "object", "properties": {"text": {"type": "string"}}},
            side_effect_profile="read",
        )

    def execute(self, input_data: dict, ctx: RuntimeContext) -> ToolResult:
        del ctx
        return ToolResult(content=str(input_data.get("text", "")).strip() or "(empty)")
