from __future__ import annotations

import json
from typing import Any

from sparrow_agent.config import load_openai_settings
from sparrow_agent.schemas.models import LLMResponse, Message, RuntimeContext, ToolCallRequest, ToolDefinition


class OpenAIResponsesModelClient:
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-5.2",
        base_url: str | None = None,
        reasoning_effort: str | None = None,
        max_output_tokens: int | None = None,
        client: object | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.reasoning_effort = reasoning_effort
        self.max_output_tokens = max_output_tokens
        self.client = client or self._build_client()

    def _build_client(self) -> object:
        from openai import OpenAI

        kwargs: dict[str, str] = {"api_key": self.api_key}
        if self.base_url:
            kwargs["base_url"] = self.base_url
        return OpenAI(**kwargs)

    def generate(
        self,
        ctx: RuntimeContext,
        system_prompts: list[str],
        tool_definitions: list[ToolDefinition] | None = None,
    ) -> LLMResponse:
        if not hasattr(self.client, "responses"):
            raise RuntimeError("OpenAI client does not support the Responses API. Upgrade to openai>=2.30.0.")

        instructions = self._build_instructions(ctx=ctx, system_prompts=system_prompts)
        request: dict[str, Any] = {
            "model": self.model,
            "instructions": instructions,
            "input": self._build_input_messages(ctx),
        }
        tools = self._build_tools(tool_definitions or [])
        if tools:
            request["tools"] = tools
        if self.reasoning_effort:
            request["reasoning"] = {"effort": self.reasoning_effort}
        if self.max_output_tokens is not None:
            request["max_output_tokens"] = self.max_output_tokens
        if ctx.previous_response_id:
            request["previous_response_id"] = ctx.previous_response_id

        response = self.client.responses.create(**request)
        raw_response = self._to_dict(response)
        output_items = raw_response.get("output", [])
        tool_calls = self._extract_tool_calls(output_items)
        thinking_blocks = self._extract_thinking_blocks(output_items)
        reasoning_content = self._extract_reasoning_content(thinking_blocks)
        text = getattr(response, "output_text", "") or raw_response.get("output_text")
        return LLMResponse(
            response_id=raw_response.get("id"),
            content=text.strip() if isinstance(text, str) and text.strip() else None,
            tool_calls=tool_calls,
            finish_reason=str(raw_response.get("status", "stop")),
            usage=self._extract_usage(raw_response.get("usage")),
            reasoning_content=reasoning_content,
            thinking_blocks=thinking_blocks or None,
            raw_response=raw_response,
        )

    @staticmethod
    def _build_instructions(ctx: RuntimeContext, system_prompts: list[str]) -> str:
        lines = [
            "You are Sparrow Agent, a lightweight assistant running in a local runtime.",
            "Use markdown documents as high-priority context.",
            "Use tools when they help complete the task, then continue the loop until done.",
            "When the user shares stable profile details, preferences, or long-term context, record them with the USER.md or MEMORY.md tools when appropriate.",
            "When the user gives the agent a nickname or name, record it in SOUL.md (agent identity), not USER.md.",
        ]
        if system_prompts:
            lines.append("Active skill prompts:\n- " + "\n- ".join(system_prompts))
        if ctx.documents:
            lines.append(
                "Workspace documents:\n- "
                + "\n- ".join(f"{item.kind}: {item.content.strip()[:800]}" for item in ctx.documents if item.content.strip())
            )
        if ctx.memories:
            lines.append("Recalled memory:\n- " + "\n- ".join(item.text for item in ctx.memories))
        return "\n\n".join(lines)

    @staticmethod
    def _build_input_messages(ctx: RuntimeContext) -> list[dict[str, Any]]:
        history = [OpenAIResponsesModelClient._map_message(message) for message in ctx.messages[-16:]]
        history.extend(OpenAIResponsesModelClient._map_message(message) for message in ctx.loop_state.observations)
        history.append({"role": "user", "content": ctx.user_input})
        return OpenAIResponsesModelClient._filter_orphan_tool_outputs(history)

    @staticmethod
    def _filter_orphan_tool_outputs(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        call_ids = {m["call_id"] for m in messages if m.get("type") == "function_call"}
        return [
            m for m in messages
            if m.get("type") != "function_call_output" or m.get("call_id") in call_ids
        ]

    @staticmethod
    def _build_tools(tool_definitions: list[ToolDefinition]) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.input_schema or {"type": "object", "properties": {}},
            }
            for tool in tool_definitions
        ]

    @staticmethod
    def _map_message(message: Message) -> dict[str, Any]:
        if message.role == "function_call":
            return {
                "type": "function_call",
                "call_id": str(message.metadata.get("tool_call_id", "")),
                "name": message.name or "",
                "arguments": message.content,
            }
        if message.role == "tool":
            tool_call_id = str(message.metadata.get("tool_call_id", "")).strip()
            if tool_call_id:
                return {
                    "type": "function_call_output",
                    "call_id": tool_call_id,
                    "output": message.content,
                }
            # Backward compatibility for older session entries without tool_call_id.
            return {"role": "assistant", "content": message.content}

        role = message.role
        if role not in {"user", "assistant"}:
            role = "assistant"
        return {"role": role, "content": message.content}

    @staticmethod
    def _to_dict(value: Any) -> dict[str, Any]:
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        if isinstance(value, dict):
            return value
        if hasattr(value, "__dict__"):
            return dict(vars(value))
        return {}

    @staticmethod
    def _extract_tool_calls(items: list[dict[str, Any]]) -> list[ToolCallRequest]:
        tool_calls: list[ToolCallRequest] = []
        for item in items:
            item_type = item.get("type")
            if item_type not in {"function_call", "tool_call"}:
                continue
            raw_arguments = item.get("arguments", {})
            if isinstance(raw_arguments, str):
                try:
                    arguments = json.loads(raw_arguments)
                except json.JSONDecodeError:
                    arguments = {"raw": raw_arguments}
            elif isinstance(raw_arguments, dict):
                arguments = raw_arguments
            else:
                arguments = {"raw": raw_arguments}
            tool_calls.append(
                ToolCallRequest(
                    id=str(item.get("call_id") or item.get("id") or ""),
                    name=str(item.get("name") or ""),
                    arguments=arguments,
                )
            )
        return tool_calls

    @staticmethod
    def _extract_thinking_blocks(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [item for item in items if item.get("type") == "reasoning"]

    @staticmethod
    def _extract_reasoning_content(items: list[dict[str, Any]]) -> str | None:
        summaries: list[str] = []
        for item in items:
            summary = item.get("summary")
            if isinstance(summary, list):
                for block in summary:
                    if isinstance(block, dict) and isinstance(block.get("text"), str):
                        summaries.append(block["text"])
            elif isinstance(summary, str):
                summaries.append(summary)
            elif isinstance(item.get("text"), str):
                summaries.append(item["text"])
        if not summaries:
            return None
        return "\n".join(text.strip() for text in summaries if text.strip()) or None

    @staticmethod
    def _extract_usage(usage: Any) -> dict[str, int]:
        if usage is None:
            return {}
        if hasattr(usage, "model_dump"):
            usage = usage.model_dump(mode="json")
        if not isinstance(usage, dict):
            return {}

        result: dict[str, int] = {}
        for key in ("input_tokens", "output_tokens", "total_tokens"):
            value = usage.get(key)
            if isinstance(value, int):
                result[key] = value

        output_details = usage.get("output_tokens_details", {})
        if isinstance(output_details, dict):
            reasoning_tokens = output_details.get("reasoning_tokens")
            if isinstance(reasoning_tokens, int):
                result["reasoning_tokens"] = reasoning_tokens

        input_details = usage.get("input_tokens_details", {})
        if isinstance(input_details, dict):
            cached_tokens = input_details.get("cached_tokens")
            if isinstance(cached_tokens, int):
                result["cached_tokens"] = cached_tokens

        return result


def build_default_model_client():
    settings = load_openai_settings()
    if not settings.get("api_key"):
        from sparrow_agent.llm.base import ConfigErrorModelClient

        return ConfigErrorModelClient(
            "OpenAI API key is not configured. Set OPENAI_API_KEY or create data/config/openai.json."
        )

    return OpenAIResponsesModelClient(
        api_key=settings["api_key"],
        model=settings.get("model", "gpt-5.2"),
        base_url=settings.get("base_url"),
        reasoning_effort=settings.get("reasoning_effort"),
        max_output_tokens=int(settings["max_output_tokens"]) if settings.get("max_output_tokens") else None,
    )
