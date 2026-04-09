# CLI Thinking Animation Design

Status: Implemented
Date: 2026-04-03

## Goal

Make the CLI feel like an interactive agent session instead of a plain request-response chatbot.

The immediate requirement is a visible waiting animation while the model is working, without pushing presentation logic into the shared runtime.

## Chosen Approach

Use a thin CLI-side spinner that wraps `runtime.run_turn(...)` in a background thread and updates the terminal from the foreground thread.

This keeps the architecture aligned with the project direction:

- core runtime stays shared and product-agnostic
- CLI remains a thin shell around the runtime
- no fake runtime state is introduced into `sparrow_agent/core/`
- future runtime progress events can replace the static spinner label later

## UX Shape

Each turn now has three visible phases:

1. user submits input
2. CLI shows `agent | thinking... <elapsed>s`
3. CLI renders a terminal-style reply block:

```text
sparrow>
  reply text...
[steps 2 | tools read_file | tokens in 120, out 48, total 168]
```

Fast turns do not show the spinner if the work finishes before the animation delay threshold.

## Why Not Stream Tokens Yet

The current runtime and model client are synchronous and do not expose incremental token events.

Adding real token streaming would require:

- model client streaming support
- ReAct loop changes for partial output handling
- adapter-safe progress/event contracts

That is a larger kernel change. The CLI spinner improves interaction now without coupling the adapter to speculative runtime behavior.

Update 2026-04-09:

- shared runtime text streaming now exists for supported model clients
- the spinner still matters as fallback state and for non-streaming phases
- this document remains the design note for the waiting animation, not the source of truth for streaming support

## Follow-Up

If runtime observability is upgraded later, the CLI should prefer real phase events such as:

- loading context
- reasoning
- calling tool
- summarizing

At that point, the spinner label can be driven by runtime state instead of a fixed `thinking` message.
