from __future__ import annotations

import json
from pathlib import Path

from sparrow_agent.core.runtime import AgentRuntime
from sparrow_agent.llm.base import EchoModelClient
from sparrow_agent.schemas.models import LLMResponse, RuntimeContext, ToolCallRequest, ToolDefinition
from sparrow_agent.storage.file_store import FileStore


def create_runtime_templates(tmp_path: Path) -> None:
    template_dir = tmp_path / "templates" / "runtime"
    (template_dir / "memory").mkdir(parents=True, exist_ok=True)
    (template_dir / "AGENTS.md").write_text("# Template AGENTS\n", encoding="utf-8")
    (template_dir / "SOUL.md").write_text("# Template SOUL\n", encoding="utf-8")
    (template_dir / "USER.md").write_text(
        (
            "# USER\n\n"
            "## Purpose\n"
            "- This file stores who the user is: profile, preferences, and stable user context.\n"
            "- Only write information about the user here.\n\n"
            "## Profile\n"
            "- Name: Not provided yet.\n"
            "- Language: (preferred language)\n\n"
            "## Preferences\n"
            "- Communication style: Not provided yet.\n"
            "- Things to avoid: Not provided yet.\n\n"
            "## Stable Context\n"
            "- Primary uses: Not provided yet.\n"
            "- Long-term context: Not provided yet.\n"
        ),
        encoding="utf-8",
    )
    (template_dir / "MEMORY.md").write_text(
        (
            "# MEMORY\n\n"
            "## Purpose\n"
            "- This file stores durable project, task, and contextual facts that should remain useful across sessions.\n"
            "- Do not use this file for agent persona or user profile details.\n"
            "- Put user-specific preferences in `USER.md` and short-lived working context in `memory/YYYY-MM-DD.md`.\n\n"
            "## Long-Term Facts\n"
            "- No long-term facts captured yet.\n\n"
            "## Ongoing Context\n"
            "- No ongoing context captured yet.\n\n"
            "## Working Notes\n"
            "- No reusable working notes captured yet.\n"
        ),
        encoding="utf-8",
    )


def build_runtime(tmp_path: Path, model_client=None, memory_window: int = 100) -> AgentRuntime:
    create_runtime_templates(tmp_path)
    file_store = FileStore(
        workspace_root=tmp_path,
        runtime_dir=tmp_path / ".sparrow",
        templates_dir=tmp_path / "templates" / "runtime",
        sessions_dir=tmp_path / ".sparrow" / "sessions",
        logs_dir=tmp_path / ".sparrow" / "logs",
        daily_memory_dir=tmp_path / ".sparrow" / "memory",
        agents_doc_path=tmp_path / ".sparrow" / "AGENTS.md",
        soul_doc_path=tmp_path / ".sparrow" / "SOUL.md",
        user_doc_path=tmp_path / ".sparrow" / "USER.md",
        memory_doc_path=tmp_path / ".sparrow" / "MEMORY.md",
    )
    return AgentRuntime(
        file_store=file_store,
        model_client=model_client or EchoModelClient(),
        memory_window=memory_window,
    )


class MemoryRefreshCheckModelClient:
    def __init__(self) -> None:
        self.calls = 0
        self.seen_user_docs: list[str] = []

    def generate(
        self,
        ctx: RuntimeContext,
        system_prompts: list[str],
        tool_definitions: list[ToolDefinition] | None = None,
    ) -> LLMResponse:
        del system_prompts, tool_definitions
        self.calls += 1
        user_doc = next((item.content for item in ctx.documents if item.kind == "user"), "")
        self.seen_user_docs.append(user_doc)
        if self.calls == 1:
            return LLMResponse(
                tool_calls=[
                    ToolCallRequest(
                        id="call_patch_1",
                        name="patch_memory_doc",
                        arguments={
                            "document": "user",
                            "operation": "upsert_kv",
                            "heading": "Profile",
                            "key": "Name",
                            "value": "Meng",
                        },
                    )
                ],
                finish_reason="tool_calls",
            )
        status = "updated" if "Name: Meng" in user_doc else "stale"
        return LLMResponse(content=status, finish_reason="stop")


class FailingModelClient:
    def generate(
        self,
        ctx: RuntimeContext,
        system_prompts: list[str],
        tool_definitions: list[ToolDefinition] | None = None,
    ) -> LLMResponse:
        del ctx, system_prompts, tool_definitions
        raise RuntimeError("simulated model failure")


class StreamingModelClient:
    def __init__(self) -> None:
        self.calls = 0

    def generate(
        self,
        ctx: RuntimeContext,
        system_prompts: list[str],
        tool_definitions: list[ToolDefinition] | None = None,
    ) -> LLMResponse:
        del ctx, system_prompts, tool_definitions
        raise AssertionError("streaming path should be used")

    def generate_stream(
        self,
        ctx: RuntimeContext,
        system_prompts: list[str],
        tool_definitions: list[ToolDefinition] | None = None,
        text_delta_callback=None,
    ) -> LLMResponse:
        del ctx, system_prompts, tool_definitions
        self.calls += 1
        if self.calls == 1:
            if text_delta_callback is not None:
                text_delta_callback("draft")
            return LLMResponse(
                tool_calls=[ToolCallRequest(id="call_1", name="echo", arguments={"text": "hi"})],
                finish_reason="tool_calls",
            )
        if text_delta_callback is not None:
            text_delta_callback("final ")
            text_delta_callback("answer")
        return LLMResponse(content="final answer", finish_reason="stop")


def test_runtime_returns_model_reply_with_documents(tmp_path: Path) -> None:
    runtime = build_runtime(tmp_path)

    result = runtime.run_turn(session_id="demo", user_input="hello world")

    assert "User said: hello world" in result.reply
    assert "Documents:" in result.reply
    assert result.llm_response is not None
    assert result.used_tools == []
    assert len(result.messages) >= 2


def test_runtime_executes_explicit_tool_command(tmp_path: Path) -> None:
    runtime = build_runtime(tmp_path)

    result = runtime.run_turn(session_id="demo", user_input='/tool echo {"text":"hi"}')

    assert result.reply == "hi"
    assert result.used_tools == ["echo"]


def test_runtime_runs_react_tool_loop(tmp_path: Path) -> None:
    model_client = EchoModelClient(
        scripted_responses=[
            LLMResponse(
                tool_calls=[ToolCallRequest(id="call_1", name="echo", arguments={"text": "tool hi"})],
                finish_reason="tool_calls",
            ),
            LLMResponse(content="final answer", finish_reason="stop"),
        ]
    )
    runtime = build_runtime(tmp_path, model_client=model_client)

    result = runtime.run_turn(session_id="demo", user_input="say hi with tools")

    assert result.reply == "final answer"
    assert result.used_tools == ["echo"]
    assert result.iterations == 2
    assert any(message.role == "tool" and message.content == "tool hi" for message in result.messages)
    # Verify function_call message is also persisted alongside tool result
    assert any(message.role == "function_call" and message.name == "echo" for message in result.messages)


def test_runtime_emits_streaming_response_events(tmp_path: Path) -> None:
    model_client = StreamingModelClient()
    runtime = build_runtime(tmp_path, model_client=model_client)
    events: list[tuple[str, dict]] = []

    result = runtime.run_turn(
        session_id="demo",
        user_input="stream please",
        response_event_callback=lambda event, payload: events.append((event, payload)),
    )

    assert result.reply == "final answer"
    assert [event for event, _ in events] == ["response.delta", "response.reset", "response.delta", "response.delta"]
    assert events[0][1]["delta"] == "draft"
    assert events[-1][1]["delta"] == "answer"


def test_runtime_refreshes_documents_after_memory_mutation_tool(tmp_path: Path) -> None:
    model_client = MemoryRefreshCheckModelClient()
    runtime = build_runtime(tmp_path, model_client=model_client)
    runtime.file_store.write_document(
        runtime.file_store.user_doc_path,
        (
            "# USER\n\n"
            "## Profile\n"
            "- Name: Not provided yet.\n"
            "- Language: Chinese\n\n"
            "## Preferences\n"
            "- Communication style: Concise and direct\n"
        ),
    )

    result = runtime.run_turn(session_id="demo", user_input="以后叫我猛哥")

    assert result.reply == "updated"
    assert len(model_client.seen_user_docs) >= 2
    assert "Name: Not provided yet." in model_client.seen_user_docs[0]
    assert "Name: Meng" in model_client.seen_user_docs[1]


def test_runtime_consolidates_long_history(tmp_path: Path) -> None:
    runtime = build_runtime(tmp_path, memory_window=4)

    runtime.run_turn(session_id="demo", user_input="one")
    runtime.run_turn(session_id="demo", user_input="two")
    runtime.run_turn(session_id="demo", user_input="three")

    result = runtime.run_turn(session_id="demo", user_input="four")

    assert result.consolidation is not None
    assert result.consolidation.triggered is True
    daily_memory = (tmp_path / ".sparrow" / "memory").glob("*.md")
    assert any("Consolidated session history" in path.read_text(encoding="utf-8") for path in daily_memory)


def test_runtime_file_tools_still_use_workspace_root(tmp_path: Path) -> None:
    runtime = build_runtime(tmp_path)
    (tmp_path / "README.md").write_text("workspace file", encoding="utf-8")

    result = runtime.run_turn(session_id="demo", user_input='/tool read_file {"path":"README.md"}')

    assert result.reply == "workspace file"


def test_runtime_persists_user_message_and_started_log_before_model_returns(tmp_path: Path) -> None:
    runtime = build_runtime(tmp_path, model_client=FailingModelClient())

    try:
        runtime.run_turn(session_id="demo", user_input="persist this")
    except RuntimeError as exc:
        assert str(exc) == "simulated model failure"
    else:
        raise AssertionError("Expected runtime to surface model failure.")

    session = runtime.file_store.load_session("demo")
    assert any(message.role == "user" and message.content == "persist this" for message in session.messages)

    log_path = next((tmp_path / ".sparrow" / "logs").glob("*.jsonl"))
    log_lines = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert any(line["status"] == "started" and line["user_input"] == "persist this" for line in log_lines)


def test_runtime_start_session_returns_onboarding_prompt_for_default_user_doc(tmp_path: Path) -> None:
    runtime = build_runtime(tmp_path)

    first = runtime.start_session(session_id="demo")
    assert "Before we start" in first.reply
    assert "1/5. What should I call you?" in first.reply


def test_runtime_start_session_is_suppressed_once_user_doc_is_filled(tmp_path: Path) -> None:
    runtime = build_runtime(tmp_path)
    runtime.file_store.write_document(
        runtime.file_store.user_doc_path,
        (
            "# USER\n\n"
            "## Profile\n"
            "- Name: Chen\n"
            "- Language: Chinese\n\n"
            "## Preferences\n"
            "- Communication style: concise\n"
            "- Things to avoid: fluff\n\n"
            "## Stable Context\n"
            "- Primary uses: planning\n"
            "- Long-term context: ongoing product work\n"
        ),
    )

    started = runtime.start_session(session_id="demo")

    assert started.reply == ""
    assert started.messages == []

    result = runtime.run_turn(session_id="demo", user_input="hello world")
    assert "User said: hello world" in result.reply


def test_runtime_start_session_is_proactive_and_idempotent(tmp_path: Path) -> None:
    runtime = build_runtime(tmp_path)

    first = runtime.start_session(session_id="demo")
    second = runtime.start_session(session_id="demo")

    assert "1/5. What should I call you?" in first.reply
    assert second.reply == ""
    assistant_messages = [message for message in second.messages if message.role == "assistant"]
    assert len(assistant_messages) == 1


def test_runtime_bootstrap_advances_one_question_at_a_time_and_updates_user_doc(tmp_path: Path) -> None:
    runtime = build_runtime(tmp_path)

    runtime.start_session(session_id="demo")
    result = runtime.run_turn(session_id="demo", user_input="Chen")

    assert result.reply == "2/5. What do you mainly want me to help you with?"
    user_doc = runtime.file_store.read_document(runtime.file_store.user_doc_path)
    assert "- Name: Chen" in user_doc
    assert "- Language: English" in user_doc


def test_runtime_bootstrap_does_not_restart_in_new_session_after_partial_answers(tmp_path: Path) -> None:
    runtime = build_runtime(tmp_path)

    runtime.start_session(session_id="demo")
    runtime.run_turn(session_id="demo", user_input="Chen")

    started = runtime.start_session(session_id="new-session")

    assert started.reply == ""


def test_runtime_bootstrap_switches_language_based_on_user_answer(tmp_path: Path) -> None:
    runtime = build_runtime(tmp_path)

    runtime.start_session(session_id="demo")
    result = runtime.run_turn(session_id="demo", user_input="叫我猛哥")

    assert result.reply == "2/5. 你主要希望我帮你做什么？"
    user_doc = runtime.file_store.read_document(runtime.file_store.user_doc_path)
    assert "- Language: Chinese" in user_doc


def test_runtime_bootstrap_completes_after_fifth_answer_and_updates_memory(tmp_path: Path) -> None:
    runtime = build_runtime(tmp_path)

    runtime.start_session(session_id="demo")
    runtime.run_turn(session_id="demo", user_input="Chen")
    runtime.run_turn(session_id="demo", user_input="Help with coding")
    runtime.run_turn(session_id="demo", user_input="Be concise")
    runtime.run_turn(session_id="demo", user_input="Avoid fluff")
    result = runtime.run_turn(session_id="demo", user_input="Remember Sparrow Agent product work")

    assert result.reply == "Thanks. I have enough to get started."
    memory_doc = runtime.file_store.read_document(runtime.file_store.memory_doc_path)
    assert "- Remember Sparrow Agent product work" in memory_doc
