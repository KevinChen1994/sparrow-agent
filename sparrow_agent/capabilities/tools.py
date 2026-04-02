from __future__ import annotations

import json

from sparrow_agent.capabilities.base import Tool
from sparrow_agent.schemas.models import RuntimeContext, ToolResult


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_names(self) -> list[str]:
        return sorted(self._tools.keys())

    def try_execute_from_input(self, user_input: str, ctx: RuntimeContext) -> tuple[str | None, ToolResult | None]:
        if not user_input.startswith("/tool "):
            return None, None

        _, _, remainder = user_input.partition("/tool ")
        tool_name, _, raw_json = remainder.partition(" ")
        tool = self.get(tool_name.strip())
        if tool is None:
            return tool_name.strip() or None, ToolResult(content=f"Unknown tool: {tool_name.strip()}")

        input_payload = {}
        if raw_json.strip():
            try:
                input_payload = json.loads(raw_json)
            except json.JSONDecodeError as exc:
                return tool.name, ToolResult(content=f"Invalid JSON input: {exc}")

        return tool.name, tool.execute(input_payload, ctx)


class EchoTool:
    name = "echo"
    description = "Echo the provided text payload."
    input_schema = {"type": "object", "properties": {"text": {"type": "string"}}}

    def execute(self, input_data: dict, ctx: RuntimeContext) -> ToolResult:
        del ctx
        text = str(input_data.get("text", "")).strip()
        return ToolResult(content=text or "(empty)")
