from __future__ import annotations

from collections.abc import Callable

from sparrow_agent.llm.base import ModelClient
from sparrow_agent.schemas.models import LLMResponse, LoopState, Message, RuntimeContext, TraceStep
from sparrow_agent.tools.registry import ToolRegistry


class ReActLoop:
    def __init__(self, model_client: ModelClient, tool_registry: ToolRegistry, halt_policy) -> None:
        self.model_client = model_client
        self.tool_registry = tool_registry
        self.halt_policy = halt_policy

    def run(
        self,
        ctx: RuntimeContext,
        system_prompts: list[str],
        trace_callback: Callable[[TraceStep], None] | None = None,
    ) -> tuple[str, LLMResponse | None, list[str], LoopState, list[TraceStep]]:
        loop_state = ctx.loop_state.model_copy()
        last_response: LLMResponse | None = None
        used_tools: list[str] = []
        trace_steps: list[TraceStep] = []

        def emit(step: TraceStep) -> None:
            trace_steps.append(step)
            if trace_callback is not None:
                trace_callback(step)

        while True:
            loop_state.iteration += 1
            emit(
                TraceStep(
                    index=len(trace_steps) + 1,
                    phase="plan",
                    title=f"Iteration {loop_state.iteration}",
                    detail="Model reasoning and planning",
                    iteration=loop_state.iteration,
                )
            )
            current_ctx = ctx.model_copy(update={"loop_state": loop_state})
            last_response = self.model_client.generate(
                ctx=current_ctx,
                system_prompts=system_prompts,
                tool_definitions=self.tool_registry.list_definitions(),
            )

            should_stop, reason = self.halt_policy.should_stop(loop_state, last_response)
            if should_stop and last_response.content:
                if reason and not last_response.content:
                    return reason, last_response, used_tools, loop_state, trace_steps
                emit(
                    TraceStep(
                        index=len(trace_steps) + 1,
                        phase="respond",
                        title="Generated response",
                        detail=reason,
                        iteration=loop_state.iteration,
                    )
                )
                return last_response.content, last_response, used_tools, loop_state, trace_steps
            if should_stop and reason:
                emit(
                    TraceStep(
                        index=len(trace_steps) + 1,
                        phase="control",
                        title="Stopped by policy",
                        detail=reason,
                        iteration=loop_state.iteration,
                    )
                )
                return reason, last_response, used_tools, loop_state, trace_steps

            if not last_response.has_tool_calls:
                emit(
                    TraceStep(
                        index=len(trace_steps) + 1,
                        phase="respond",
                        title="Generated response",
                        iteration=loop_state.iteration,
                    )
                )
                return last_response.content or "(empty response)", last_response, used_tools, loop_state, trace_steps

            tool_messages: list[Message] = []
            for tool_call in last_response.tool_calls:
                emit(
                    TraceStep(
                        index=len(trace_steps) + 1,
                        phase="tool_call",
                        title=f"Calling {tool_call.name}",
                        tool_name=tool_call.name,
                        iteration=loop_state.iteration,
                    )
                )
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
                emit(
                    TraceStep(
                        index=len(trace_steps) + 1,
                        phase="tool_result",
                        title=f"Observed {tool_call.name}",
                        detail=tool_result.content[:120],
                        tool_name=tool_call.name,
                        iteration=loop_state.iteration,
                    )
                )

            loop_state.tool_calls.extend(last_response.tool_calls)
            loop_state.observations.extend(tool_messages)

            should_stop, reason = self.halt_policy.should_stop(loop_state, None)
            if should_stop:
                if last_response.content:
                    emit(
                        TraceStep(
                            index=len(trace_steps) + 1,
                            phase="respond",
                            title="Generated response",
                            detail=reason,
                            iteration=loop_state.iteration,
                        )
                    )
                    return last_response.content, last_response, used_tools, loop_state, trace_steps
                emit(
                    TraceStep(
                        index=len(trace_steps) + 1,
                        phase="control",
                        title="Stopped by policy",
                        detail=reason or "(stopped)",
                        iteration=loop_state.iteration,
                    )
                )
                return reason or "(stopped)", last_response, used_tools, loop_state, trace_steps
