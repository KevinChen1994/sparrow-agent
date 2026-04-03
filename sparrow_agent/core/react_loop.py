from __future__ import annotations

from typing import Callable

from sparrow_agent.llm.base import ModelClient
from sparrow_agent.schemas.models import DocumentSnapshot, LLMResponse, LoopState, Message, RuntimeContext
from sparrow_agent.tools.registry import ToolRegistry


class ReActLoop:
    def __init__(
        self,
        model_client: ModelClient,
        tool_registry: ToolRegistry,
        halt_policy,
        refresh_documents: Callable[[], list[DocumentSnapshot]] | None = None,
    ) -> None:
        self.model_client = model_client
        self.tool_registry = tool_registry
        self.halt_policy = halt_policy
        self.refresh_documents = refresh_documents

    def run(self, ctx: RuntimeContext, system_prompts: list[str]) -> tuple[str, LLMResponse | None, list[str], LoopState]:
        loop_state = ctx.loop_state.model_copy()
        last_response: LLMResponse | None = None
        used_tools: list[str] = []

        while True:
            loop_state.iteration += 1
            current_ctx = ctx.model_copy(update={"loop_state": loop_state})
            last_response = self.model_client.generate(
                ctx=current_ctx,
                system_prompts=system_prompts,
                tool_definitions=self.tool_registry.list_definitions(),
            )

            should_stop, reason = self.halt_policy.should_stop(loop_state, last_response)
            if should_stop and last_response.content:
                if reason and not last_response.content:
                    return reason, last_response, used_tools, loop_state
                return last_response.content, last_response, used_tools, loop_state
            if should_stop and reason:
                return reason, last_response, used_tools, loop_state

            if not last_response.has_tool_calls:
                return last_response.content or "(empty response)", last_response, used_tools, loop_state

            tool_messages: list[Message] = []
            for tool_call in last_response.tool_calls:
                tool_result = self.tool_registry.execute(tool_call.name, tool_call.arguments, current_ctx)
                used_tools.append(tool_call.name)
                tool_messages.append(
                    Message(
                        role="tool",
                        name=tool_call.name,
                        content=tool_result.content,
                        metadata={"tool_call_id": tool_call.id, **tool_result.metadata},
                    )
                )

            loop_state.tool_calls.extend(last_response.tool_calls)
            loop_state.observations.extend(tool_messages)
            if any(self._tool_mutates_memory(tool_call.name) for tool_call in last_response.tool_calls):
                refreshed = self._refresh_documents()
                if refreshed is not None:
                    ctx = ctx.model_copy(update={"documents": refreshed})

            should_stop, reason = self.halt_policy.should_stop(loop_state, None)
            if should_stop:
                if last_response.content:
                    return last_response.content, last_response, used_tools, loop_state
                return reason or "(stopped)", last_response, used_tools, loop_state

    def _tool_mutates_memory(self, tool_name: str) -> bool:
        definition = self.tool_registry.get_definition(tool_name)
        return bool(definition and definition.mutates_memory)

    def _refresh_documents(self) -> list[DocumentSnapshot] | None:
        if self.refresh_documents is None:
            return None
        try:
            return self.refresh_documents()
        except Exception:
            return None
