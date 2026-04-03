from __future__ import annotations

from pathlib import Path

from sparrow_agent.core.runtime import AgentRuntime
from sparrow_agent.llm.base import EchoModelClient
from sparrow_agent.memory.store import MemoryStore
from sparrow_agent.schemas.models import LLMResponse, RuntimeContext, ToolCallRequest, ToolDefinition
from sparrow_agent.storage.file_store import FileStore


def create_runtime_templates(tmp_path: Path) -> None:
    template_dir = tmp_path / "templates" / "runtime"
    (template_dir / "memory").mkdir(parents=True, exist_ok=True)
    (template_dir / "AGENTS.md").write_text("# Template AGENTS\n", encoding="utf-8")
    (template_dir / "SOUL.md").write_text("# Template SOUL\n", encoding="utf-8")
    (template_dir / "USER.md").write_text("# Template USER\n", encoding="utf-8")
    (template_dir / "MEMORY.md").write_text("# Template MEMORY\n", encoding="utf-8")


def build_runtime(tmp_path: Path, model_client=None, memory_window: int = 100) -> AgentRuntime:
    create_runtime_templates(tmp_path)
    file_store = FileStore(
        workspace_root=tmp_path,
        runtime_dir=tmp_path / ".sparrow",
        templates_dir=tmp_path / "templates" / "runtime",
        sessions_dir=tmp_path / ".sparrow" / "sessions",
        memories_dir=tmp_path / ".sparrow" / "memories",
        logs_dir=tmp_path / ".sparrow" / "logs",
        daily_memory_dir=tmp_path / ".sparrow" / "memory",
        agents_doc_path=tmp_path / ".sparrow" / "AGENTS.md",
        soul_doc_path=tmp_path / ".sparrow" / "SOUL.md",
        user_doc_path=tmp_path / ".sparrow" / "USER.md",
        memory_doc_path=tmp_path / ".sparrow" / "MEMORY.md",
    )
    return AgentRuntime(
        file_store=file_store,
        memory_store=MemoryStore(file_store),
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
                            "key": "Preferred name",
                            "value": "Meng",
                        },
                    )
                ],
                finish_reason="tool_calls",
            )
        status = "updated" if "Preferred name: Meng" in user_doc else "stale"
        return LLMResponse(content=status, finish_reason="stop")


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


def test_runtime_refreshes_documents_after_memory_mutation_tool(tmp_path: Path) -> None:
    model_client = MemoryRefreshCheckModelClient()
    runtime = build_runtime(tmp_path, model_client=model_client)
    runtime.file_store.write_document(
        runtime.file_store.user_doc_path,
        (
            "# USER\n\n"
            "## Profile\n"
            "- Preferred name: Unknown\n"
            "- Language: Chinese\n\n"
            "## Preferences\n"
            "- Communication style: Concise and direct\n"
        ),
    )

    result = runtime.run_turn(session_id="demo", user_input="以后叫我猛哥")

    assert result.reply == "updated"
    assert len(model_client.seen_user_docs) >= 2
    assert "Preferred name: Unknown" in model_client.seen_user_docs[0]
    assert "Preferred name: Meng" in model_client.seen_user_docs[1]


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


def test_runtime_start_session_returns_onboarding_prompt_for_default_user_doc(tmp_path: Path) -> None:
    runtime = build_runtime(tmp_path)

    first = runtime.start_session(session_id="demo")
    assert "Before we start" in first.reply
    assert "1. What should I call you?" in first.reply
    assert "You can answer any or all of them now" in first.reply


def test_runtime_start_session_is_suppressed_once_user_doc_is_filled(tmp_path: Path) -> None:
    runtime = build_runtime(tmp_path)
    runtime.file_store.write_document(
        runtime.file_store.user_doc_path,
        "# USER\n\n## Profile\n- Preferred name: Chen\n\n## Preferences\n- Language: Chinese\n",
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

    assert "1. What should I call you?" in first.reply
    assert second.reply == ""
    assistant_messages = [message for message in second.messages if message.role == "assistant"]
    assert len(assistant_messages) == 1
