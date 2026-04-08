from __future__ import annotations

from typing import Protocol

from sparrow_agent.schemas.models import LLMResponse, RuntimeContext, ToolDefinition


class ModelClient(Protocol):
    def generate(
        self,
        ctx: RuntimeContext,
        system_prompts: list[str],
        tool_definitions: list[ToolDefinition] | None = None,
    ) -> LLMResponse: ...


class EchoModelClient:
    """Fallback model for scaffolding and tests."""

    def __init__(self, scripted_responses: list[LLMResponse] | None = None) -> None:
        self.scripted_responses = scripted_responses or []

    def generate(
        self,
        ctx: RuntimeContext,
        system_prompts: list[str],
        tool_definitions: list[ToolDefinition] | None = None,
    ) -> LLMResponse:
        del tool_definitions
        if self.scripted_responses:
            return self.scripted_responses.pop(0)

        prompt_lines = []
        if system_prompts:
            prompt_lines.append("Active prompts: " + " | ".join(system_prompts))
        if ctx.documents:
            prompt_lines.append("Documents: " + " | ".join(doc.kind for doc in ctx.documents))
        prompt_lines.append(f"User said: {ctx.user_input}")
        return LLMResponse(content="\n".join(prompt_lines), finish_reason="stop")


class ConfigErrorModelClient:
    def __init__(self, message: str) -> None:
        self.message = message

    def generate(
        self,
        ctx: RuntimeContext,
        system_prompts: list[str],
        tool_definitions: list[ToolDefinition] | None = None,
    ) -> LLMResponse:
        del ctx, system_prompts, tool_definitions
        return LLMResponse(content=self.message, finish_reason="error")
