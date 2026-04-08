# Sparrow Agent

## Project Definition

Sparrow Agent is a lightweight personal Agent kernel.

It is for:

- a local-first single-Agent runtime
- a practical multi-step ReAct loop
- markdown-based memory that stays inspectable
- thin CLI and Web shells on one shared core
- controlled and reliable tool use

It is not for:

- a multi-Agent orchestration system
- a workflow engine
- a plugin marketplace
- a cloud runtime platform
- a general framework for every Agent use case

## Product Direction

Keep the project focused on one outcome:

Build a small but capable personal Agent that gets better through use without becoming operationally heavy.

Near-term priorities:

1. Make the project runnable end-to-end.
2. Improve markdown memory quality.
3. Strengthen runtime governance and observability.
4. Keep adapters in `apps/` thin.
5. Improve tool-use safety and reliability.

## Working Workflow

Start work in this order:

1. Read `AGENTS.md`.
2. Read the relevant document in `docs/`.
3. Read `README.md` before running or validating anything.

Documentation is the long-term memory for development work. Important decisions, plans, and deferred ideas must be written down instead of left in chat history.

## Environment Rule

`README.md` is the source of truth for environment setup.

Before development, testing, or runtime verification:

- set up the project environment from `README.md`
- run validation inside that environment
- avoid mixing checks with an unprepared system environment

## Document System

`AGENTS.md` is the entry point for development-management documents.

### Root Documents

- `AGENTS.md`
  High-level project definition, document rules, and links to the current plan.
- `README.md`
  Operator-facing setup and run instructions.

### `docs/`

- `docs/plans/`
  Active plans, design notes that still matter, and staged execution documents.
- `docs/todos/`
  Deferred work that is intentionally not on the current path.
- `docs/reviews/`
  Optional space for audits or retrospectives when needed.

### Runtime Documents

Runtime documents under `.sparrow/` are not part of development management.

- `.sparrow/AGENTS.md`
  Runtime operating rules.
- `.sparrow/SOUL.md`
  Runtime persona and tone.
- `.sparrow/USER.md`
  Stable user profile and preferences.
- `.sparrow/MEMORY.md`
  Durable runtime memory.
- `.sparrow/memory/`
  Daily runtime working memory.

## Document Responsibilities

Keep document ownership simple:

- `AGENTS.md` stores stable project-level rules and document boundaries.
- `docs/plans/` stores active execution direction and non-trivial design decisions.
- `docs/todos/` stores ideas that are useful later but not active now.
- runtime documents under `.sparrow/` store runtime context only.

## Documentation Rules

All project documents should stay short, explicit, and low-ceremony.

Rules:

- One document should have one clear job.
- Prefer short sections and bullets over long prose.
- Put stable rules in `AGENTS.md`, not in plan files.
- Put active execution detail in one current plan, not in multiple overlapping documents.
- Put deferred ideas in `docs/todos/`, not inside active plans.
- Do not repeat project positioning, document boundaries, or priority lists across files unless they are truly different.
- When updating direction, edit the current authoritative document instead of creating a near-duplicate.
- If a document starts mixing overview, plan, and backlog, split it by responsibility.
- If a section does not change implementation decisions, shorten it or remove it.

Preferred style:

- start with the conclusion
- keep headings literal
- keep lists flat
- record decisions in plain language
- avoid speculative detail

## Current Active Plan

Current execution lives in:

- `docs/plans/2026-03-20-sparrow-agent-next-development-plan.md`

Approved order:

1. Make bootstrap and review flow runnable end-to-end.
2. Improve memory quality and promotion logic.
3. Strengthen runtime governance and observability.
4. Upgrade consolidation and context control.
5. Improve thin CLI and Web shells.
6. Clean up tool governance and installation flow.

## Working Rules

- Prefer depth over breadth.
- Strengthen the personal Agent kernel before expanding scope.
- Keep core behavior in `sparrow_agent/core/`.
- Keep adapters in `apps/` thin and shared-runtime driven.
- Prefer documentation that helps the next session recover context quickly.
