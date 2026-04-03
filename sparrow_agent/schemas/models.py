from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Message(BaseModel):
    role: Literal["system", "user", "assistant", "tool"] = "user"
    content: str
    created_at: datetime = Field(default_factory=utc_now)
    name: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryItem(BaseModel):
    text: str
    source: str = "user"
    created_at: datetime = Field(default_factory=utc_now)
    tags: list[str] = Field(default_factory=list)


class SessionRecord(BaseModel):
    session_id: str
    messages: list[Message] = Field(default_factory=list)
    last_response_id: str | None = None
    last_consolidated_index: int = 0
    updated_at: datetime = Field(default_factory=utc_now)


class DocumentSnapshot(BaseModel):
    kind: Literal["agents", "soul", "user", "memory", "daily"]
    path: str
    content: str
    updated_at: datetime | None = None


class ToolDefinition(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any] = Field(default_factory=dict)
    side_effect_profile: Literal["read", "write", "external"] = "read"
    mutates_memory: bool = False
    requires_confirmation: bool = False


class ToolCallRequest(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class LoopState(BaseModel):
    iteration: int = 0
    max_iterations: int = 40
    stop_requested: bool = False
    observations: list[Message] = Field(default_factory=list)
    tool_calls: list[ToolCallRequest] = Field(default_factory=list)


class ConsolidationResult(BaseModel):
    triggered: bool = False
    reason: str | None = None
    daily_summary: str | None = None
    memory_update: str | None = None
    new_last_consolidated_index: int | None = None


class RuntimeContext(BaseModel):
    session_id: str
    user_input: str
    messages: list[Message]
    memories: list[MemoryItem]
    active_skills: list[str]
    documents: list[DocumentSnapshot] = Field(default_factory=list)
    previous_response_id: str | None = None
    loop_state: LoopState = Field(default_factory=LoopState)


class LLMResponse(BaseModel):
    response_id: str | None = None
    content: str | None = None
    tool_calls: list[ToolCallRequest] = Field(default_factory=list)
    finish_reason: str = "stop"
    usage: dict[str, int] = Field(default_factory=dict)
    reasoning_content: str | None = None
    thinking_blocks: list[dict[str, Any]] | None = None
    raw_response: dict[str, Any] | None = None

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


class TraceStep(BaseModel):
    index: int
    phase: Literal["plan", "tool_call", "tool_result", "respond", "control"]
    title: str
    detail: str | None = None
    tool_name: str | None = None
    iteration: int | None = None


class TurnResult(BaseModel):
    session_id: str
    reply: str
    messages: list[Message]
    used_skills: list[str] = Field(default_factory=list)
    used_tools: list[str] = Field(default_factory=list)
    llm_response: LLMResponse | None = None
    iterations: int = 0
    consolidation: ConsolidationResult | None = None
    trace_steps: list[TraceStep] = Field(default_factory=list)
