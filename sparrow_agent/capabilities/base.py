from __future__ import annotations

from typing import Protocol

from sparrow_agent.schemas.models import RuntimeContext, ToolResult


class Tool(Protocol):
    name: str
    description: str
    input_schema: dict

    def execute(self, input_data: dict, ctx: RuntimeContext) -> ToolResult: ...


class Skill(Protocol):
    name: str
    description: str

    def matches(self, ctx: RuntimeContext) -> bool: ...
    def build_prompt(self, ctx: RuntimeContext) -> str: ...
