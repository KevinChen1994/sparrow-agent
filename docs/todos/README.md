# Sparrow Agent Deferred Work

Use this directory only for work that is intentionally not on the current execution path.

## Rules

- Keep entries short.
- Record the item, why it is deferred, and what should trigger revisiting it.
- Do not put active implementation detail here.
- If work becomes active, move it into `docs/plans/`.

## Current Deferred Items

- Random default session id
  Defer until session lifecycle and persistence behavior are being tightened. When no `session-id` is provided, stop reusing `default` and generate a random session id instead.

- Richer CLI animation and streaming output
  Defer until runtime observability and event shapes are clearer.

- Multi-Agent orchestration
  Defer until the single-Agent kernel is strong and stable.

- Compact then handoff
  Defer until consolidation and context control are more mature.
