# Sparrow Agent Next Development Plan

Status: Active
Last Confirmed: 2026-04-08

> For Claude: use this file as the current execution plan. Keep repository-level positioning and document rules in `AGENTS.md`.

**Goal:** Make Sparrow Agent genuinely usable end-to-end, then improve memory quality, runtime control, and thin product-shell review flows.

---

## Plan Rules

This file should stay execution-focused.

- Do not repeat repository positioning from `AGENTS.md`.
- Keep only active priorities, confirmed decisions, and deliverables here.
- Move deferred or speculative ideas to `docs/todos/`.

## Current Milestone

### P0: Make The Project Genuinely Runnable

This is the immediate milestone.

Definition of done:

- bootstrap starts explicitly in a usable way
- first-run guidance works in real sessions
- `SOUL.md` update flow works
- direct `SOUL.md` edits are applied safely and predictably
- `USER.md` can be updated through the intended path
- CLI and Web can exercise the same shared lifecycle
- stop and review flow are usable enough for real testing

Confirmed direction:

- bootstrap should start proactively during session initialization
- bootstrap should ask one question at a time inside the active session
- if the user has already answered bootstrap questions, later sessions should not restart it aggressively
- language should default to English and switch when the user's language can be inferred

## Confirmed Decisions

### Memory Strategy

Runtime memory remains markdown-first.

- do not add a separate structured `.sparrow/memories/` store
- durable memory belongs in `MEMORY.md`
- short-lived working context belongs in `.sparrow/memory/YYYY-MM-DD.md`

## Next Phases

P0 is the current milestone above. The phases below come after that.

### P1: Memory Quality

Goal:
Improve the quality of markdown memory, not just persistence.

Deliverables:

- section-aware updates for `USER.md` and `MEMORY.md`
- clear promotion rules from daily memory to long-term memory
- deduplication of repeated facts and preferences
- tighter boundaries between `USER.md`, `MEMORY.md`, and daily memory

### P2: Runtime Governance

Goal:
Make the loop easier to trust and debug.

Deliverables:

- explicit loop trace or step log
- stronger halt policy for repeated failure or no-progress cases
- confirmation handling for tools marked `requires_confirmation`
- safer execution path for mutating tools
- optional user-visible progress state for long turns

### P3: Consolidation Upgrade

Goal:
Turn consolidation into a real context-management subsystem.

Deliverables:

- token-aware trigger policy
- model-assisted consolidation for older session chunks
- separate outputs for daily summary and long-term memory candidate
- better session trimming after consolidation
- tests for consolidation quality and boundaries

### P4: Thin Product Shell Improvements

Goal:
Keep CLI and Web thin while exposing the real Agent lifecycle.

Deliverables:

- CLI support for bootstrap prompts, `SOUL.md` updates, and `/stop`
- Web support for bootstrap state and `SOUL.md` inspection or editing
- richer runtime response payloads for progress, review, and status

### P5: Tool Governance Cleanup

Goal:
Make tools safer and easier to extend without expanding platform scope.

Deliverables:

- tool manifest or registration metadata with side-effect profile
- runtime confirmation handling for dangerous tools
- basic manual tool installation or registration flow
- documentation for adding tools
- cleanup of legacy tool paths

## What Is Still Thin

- memory updates are still too append-oriented
- consolidation is still too simple
- runtime governance exists but is not strong enough yet
- product shells still expose too little review and progress state

## Not In This Plan

Keep these out of the active path for now:

- multi-Agent orchestration
- workflow-style execution systems
- platform expansion
- cloud-heavy operational features

Record future work under `docs/todos/`.
