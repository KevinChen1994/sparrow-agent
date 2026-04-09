from __future__ import annotations

import json
from pathlib import Path

from sparrow_agent import config
from sparrow_agent.llm.base import ConfigErrorModelClient
from sparrow_agent.llm.openai_client import OpenAIResponsesModelClient, build_default_model_client
from sparrow_agent.schemas.models import Message, RuntimeContext


class FakeResponsesAPI:
    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.stream_calls: list[dict] = []

    @staticmethod
    def _build_response():
        class Response:
            output_text = "stubbed response"

            def model_dump(self, mode="json"):
                del mode
                return {
                    "id": "resp_123",
                    "status": "completed",
                    "output_text": "stubbed response",
                    "usage": {
                        "input_tokens": 11,
                        "output_tokens": 7,
                        "total_tokens": 18,
                        "output_tokens_details": {"reasoning_tokens": 3},
                    },
                    "output": [
                        {
                            "type": "reasoning",
                            "summary": [{"text": "Checked prior memory and planned the answer."}],
                        },
                        {
                            "type": "function_call",
                            "id": "call_1",
                            "name": "search_docs",
                            "arguments": "{\"query\":\"sparrow\"}",
                        },
                    ],
                }

        return Response()

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._build_response()

    def stream(self, **kwargs):
        self.stream_calls.append(kwargs)
        response = self._build_response()

        class Event:
            def __init__(self, event_type: str, delta: str = "") -> None:
                self.type = event_type
                self.delta = delta

        class Stream:
            def __iter__(self):
                yield Event("response.output_text.delta", "stubbed ")
                yield Event("response.output_text.delta", "response")

            def get_final_response(self):
                return response

        class Manager:
            def __enter__(self):
                return Stream()

            def __exit__(self, exc_type, exc, tb):
                del exc_type, exc, tb
                return None

        return Manager()


class FakeOpenAIClient:
    def __init__(self) -> None:
        self.responses = FakeResponsesAPI()


class FakeLegacyOpenAIClient:
    pass


def test_load_openai_settings_reads_file(tmp_path: Path, monkeypatch) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_path = config_dir / "openai.json"
    config_path.write_text(
        json.dumps({"api_key": "file-key", "model": "gpt-test", "base_url": "https://example.com"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "OPENAI_CONFIG_PATH", config_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

    settings = config.load_openai_settings()

    assert settings["api_key"] == "file-key"
    assert settings["model"] == "gpt-test"
    assert settings["base_url"] == "https://example.com"


def test_default_model_client_requires_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.setattr(config, "OPENAI_CONFIG_PATH", Path("/tmp/does-not-exist.json"))

    client = build_default_model_client()

    assert isinstance(client, ConfigErrorModelClient)


def test_openai_client_uses_responses_api() -> None:
    fake_client = FakeOpenAIClient()
    client = OpenAIResponsesModelClient(api_key="test", model="gpt-test", client=fake_client)
    ctx = RuntimeContext(
        session_id="demo",
        user_input="hello",
        messages=[Message(role="assistant", content="previous")],
        active_skills=["memory-capture"],
        previous_response_id="resp_prev",
    )

    response = client.generate(ctx=ctx, system_prompts=["Be concise."])

    assert response.content == "stubbed response"
    assert response.response_id == "resp_123"
    assert response.reasoning_content == "Checked prior memory and planned the answer."
    assert response.usage["reasoning_tokens"] == 3
    assert response.tool_calls[0].name == "search_docs"
    call = fake_client.responses.calls[0]
    assert call["model"] == "gpt-test"
    assert call["input"][-1] == {"role": "user", "content": "hello"}
    assert "Be concise." in call["instructions"]
    assert call["previous_response_id"] == "resp_prev"


def test_openai_client_maps_tool_message_to_function_call_output() -> None:
    fake_client = FakeOpenAIClient()
    client = OpenAIResponsesModelClient(api_key="test", model="gpt-test", client=fake_client)
    ctx = RuntimeContext(
        session_id="demo",
        user_input="continue",
        messages=[
            Message(
                role="function_call",
                name="read_file",
                content='{"path":"test.txt"}',
                metadata={"tool_call_id": "call_tool_123"},
            ),
            Message(
                role="tool",
                name="read_file",
                content="file content",
                metadata={"tool_call_id": "call_tool_123"},
            )
        ],
        active_skills=[],
    )

    client.generate(ctx=ctx, system_prompts=[])

    call = fake_client.responses.calls[0]
    assert call["input"][0] == {
        "type": "function_call",
        "call_id": "call_tool_123",
        "name": "read_file",
        "arguments": '{"path":"test.txt"}',
    }
    assert call["input"][1] == {
        "type": "function_call_output",
        "call_id": "call_tool_123",
        "output": "file content",
    }
    assert call["input"][-1] == {"role": "user", "content": "continue"}


def test_openai_client_includes_reasoning_effort() -> None:
    fake_client = FakeOpenAIClient()
    client = OpenAIResponsesModelClient(
        api_key="test",
        model="gpt-test",
        client=fake_client,
        reasoning_effort="high",
        max_output_tokens=2048,
    )
    ctx = RuntimeContext(
        session_id="demo",
        user_input="hello",
        messages=[],
        active_skills=[],
    )

    client.generate(ctx=ctx, system_prompts=[])

    call = fake_client.responses.calls[0]
    assert call["reasoning"] == {"effort": "high"}
    assert call["max_output_tokens"] == 2048
    assert call["timeout"] == 120.0


def test_openai_client_streams_text_deltas() -> None:
    fake_client = FakeOpenAIClient()
    client = OpenAIResponsesModelClient(api_key="test", model="gpt-test", client=fake_client)
    ctx = RuntimeContext(
        session_id="demo",
        user_input="hello",
        messages=[],
        active_skills=[],
    )
    chunks: list[str] = []

    response = client.generate_stream(
        ctx=ctx,
        system_prompts=[],
        text_delta_callback=chunks.append,
    )

    assert chunks == ["stubbed ", "response"]
    assert response.content == "stubbed response"
    assert fake_client.responses.stream_calls[0]["input"][-1] == {"role": "user", "content": "hello"}


def test_openai_client_requires_responses_api() -> None:
    client = OpenAIResponsesModelClient(api_key="test", model="gpt-test", client=FakeLegacyOpenAIClient())
    ctx = RuntimeContext(
        session_id="demo",
        user_input="hello",
        messages=[],
        active_skills=[],
    )

    try:
        client.generate(ctx=ctx, system_prompts=[], tool_definitions=[])
    except RuntimeError as exc:
        assert "Responses API" in str(exc)
    else:
        raise AssertionError("Expected OpenAIResponsesModelClient to reject clients without responses support.")


def test_orphan_tool_outputs_are_filtered() -> None:
    fake_client = FakeOpenAIClient()
    client = OpenAIResponsesModelClient(api_key="test", model="gpt-test", client=fake_client)
    ctx = RuntimeContext(
        session_id="demo",
        user_input="continue",
        messages=[
            Message(
                role="tool",
                name="read_file",
                content="orphaned result",
                metadata={"tool_call_id": "call_orphan"},
            )
        ],
        active_skills=[],
    )

    client.generate(ctx=ctx, system_prompts=[])

    call = fake_client.responses.calls[0]
    # Orphaned function_call_output should be filtered out
    assert len(call["input"]) == 1
    assert call["input"][0] == {"role": "user", "content": "continue"}


def test_filter_orphan_tool_outputs_keeps_paired_messages() -> None:
    messages = [
        {"type": "function_call", "call_id": "call_1", "name": "echo", "arguments": "{}"},
        {"type": "function_call_output", "call_id": "call_1", "output": "ok"},
        {"type": "function_call_output", "call_id": "call_orphan", "output": "orphaned"},
        {"role": "user", "content": "hello"},
    ]
    result = OpenAIResponsesModelClient._filter_orphan_tool_outputs(messages)
    assert len(result) == 3
    assert result[0]["type"] == "function_call"
    assert result[1]["type"] == "function_call_output"
    assert result[2]["role"] == "user"
