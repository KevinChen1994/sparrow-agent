# Response Streaming Design

Status: Implemented
Date: 2026-04-09

## Conclusion

Sparrow Agent now streams assistant text through the shared runtime instead of faking streaming in the adapters.

## Scope

This change is intentionally narrow:

- stream model text deltas for assistant output
- keep the ReAct loop and tool execution model intact
- let Web and interactive CLI consume the same runtime-level events

It does not try to stream every runtime phase or make tool execution incremental.

## Design

The streaming path starts in `sparrow_agent/llm/openai_client.py`.

- `OpenAIResponsesModelClient.generate_stream(...)` uses the OpenAI Responses streaming API
- `response.output_text.delta` events are forwarded as text deltas
- the final accumulated response is still normalized into `LLMResponse`

The shared runtime passes those deltas upward:

- `ReActLoop.run(...)` accepts a response-event callback
- `AgentRuntime.run_turn(...)` forwards the callback without adding adapter logic
- Web turns runtime events into SSE events
- the interactive CLI updates the pending assistant block as deltas arrive

## Tool-Loop Rule

Streaming is only guaranteed to represent the current model iteration.

If a streamed model iteration later requests tools, the runtime emits a reset event before the next iteration continues. This keeps adapters thin while avoiding a larger redesign of the tool loop.

## Why This Shape

This keeps the project aligned with the repository rules:

- shared behavior stays in the kernel
- adapters stay thin
- the change is useful now without turning the runtime into a workflow engine

The next logical upgrade, if needed later, is richer runtime event types for explicit phase and tool progress.
