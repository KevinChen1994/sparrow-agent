from __future__ import annotations

import json

from sparrow_agent.schemas.models import RuntimeContext, ToolDefinition, ToolResult
from sparrow_agent.tools.base import Tool


class ToolRegistry:
    def __init__(self, tools: list[Tool] | None = None) -> None:
        self._tools: dict[str, Tool] = {}
        for tool in tools or []:
            self.register(tool)

    def register(self, tool: Tool) -> None:
        self._tools[tool.definition().name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_definitions(self) -> list[ToolDefinition]:
        return [tool.definition() for _, tool in sorted(self._tools.items())]

    def execute(self, name: str, input_data: dict, ctx: RuntimeContext) -> ToolResult:
        tool = self.get(name)
        if tool is None:
            return ToolResult(content=f"Unknown tool: {name}")
        return tool.execute(input_data, ctx)

    def try_execute_explicit_command(self, user_input: str, ctx: RuntimeContext) -> tuple[str | None, ToolResult | None]:
        if not user_input.startswith("/tool "):
            return None, None

        _, _, remainder = user_input.partition("/tool ")
        tool_name, _, raw_json = remainder.partition(" ")
        payload = {}
        if raw_json.strip():
            try:
                payload = json.loads(raw_json)
            except json.JSONDecodeError as exc:
                return tool_name.strip() or None, ToolResult(content=f"Invalid JSON input: {exc}")
        return tool_name.strip() or None, self.execute(tool_name.strip(), payload, ctx)
