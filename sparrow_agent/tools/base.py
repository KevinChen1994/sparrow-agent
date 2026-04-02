from __future__ import annotations

from typing import Protocol

from sparrow_agent.schemas.models import RuntimeContext, ToolDefinition, ToolResult


class Tool(Protocol):
    def definition(self) -> ToolDefinition: ...

    def execute(self, input_data: dict, ctx: RuntimeContext) -> ToolResult: ...
