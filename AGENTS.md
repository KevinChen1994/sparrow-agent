# Sparrow Agent

## Project Positioning

Sparrow Agent is a lightweight personal Agent kernel.

It is not trying to become a large Agent platform, a general-purpose Agent framework, or a heavy runtime system.

Its main job is to provide a strong local-first single-Agent core for personal assistant use cases:

- a practical multi-step ReAct loop
- inspectable markdown-based memory
- thin CLI and Web shells around one shared runtime
- controlled tool use

## Architectural Identity

This repository mainly belongs to the Agent-kernel layer, with a small product shell around it.

It is closer to:

- a lightweight personal Agent kernel
- a local-first single-Agent runtime
- an opinionated core for a personal assistant

It is not primarily:

- a pure framework layer
- a general runtime/platform layer

## Product Direction

The project should stay focused on one outcome:

Build a small but capable personal Agent that gets better through use, without becoming operationally heavy.

The main sources of value should be:

- stronger single-Agent task completion
- better personalization
- better markdown memory quality
- better tool-use reliability

## Product Shell Direction

The current product-shell direction is:

- CLI is the primary way users should use Sparrow Agent.
- Web should stay a thin control console around the shared runtime.
- Web is for session visibility, review, confirmation, progress, and memory inspection.
- Web should not become a separate full product or absorb core Agent logic.
- IM-based control is a promising later direction, but it is not the current primary mode.
- Keep one shared runtime and keep adapters in `apps/` thin.

## AI-First Development Strategy

This project is developed in an AI-first way.

The main constraint of AI-first development is limited context. Important instructions, decisions, and unfinished ideas cannot rely on chat memory alone. They must be written into project documents so future sessions can recover state reliably.

Because of that, this repository uses documentation as long-term project memory.

The intended workflow is:

1. Read `AGENTS.md` first at the beginning of development work.
2. Use `AGENTS.md` as the project overall and document directory.
3. When a task requires more detail, jump from `AGENTS.md` to the relevant document in `docs/`.
4. Write new decisions, plans, and deferred ideas back into documents instead of relying on temporary conversation context.

## Environment Rule

Before active development, testing, or runtime verification, the project environment should be set up from `README.md`.

This applies both to:

- project users running Sparrow Agent
- future AI development sessions working in this repository

Working rule:

- treat `README.md` as the source of truth for environment setup
- establish the project environment first
- run future commands, tests, CLI checks, and server checks inside that configured environment
- avoid mixing project execution with an unprepared system environment when validating behavior

## Near-Term Priorities

Prefer depth over breadth.

Near-term development should prioritize:

1. Strengthening the shared single-Agent loop in `sparrow_agent/core/`.
2. Improving markdown memory promotion, recall, and consolidation.
3. Making bootstrap and personalization flows explicit and reliable.
4. Adding tool governance such as confirmation and mutation boundaries.
5. Keeping adapters in `apps/` thin and the kernel reusable.

## Current Execution Strategy

The current execution strategy is:

1. First make the whole project runnable end-to-end.
2. After the runtime and product shell are in a usable state, introduce explicit ToDo management for deferred work.
3. Keep using documents to preserve direction, progress, and deferred ideas across AI sessions.

This means ToDo management is planned, but it is not the first milestone. The first milestone is getting the project to run cleanly and reliably.

## Document System

`AGENTS.md` is the documentation entry point for this repository.

It serves two roles:

- the overall description of what Sparrow Agent is and is not
- the directory for project documents and how they should be used

### Document Reading Order

When working on this repository for development and project management, prefer this reading order:

1. `AGENTS.md`
2. relevant document in `docs/`
3. `README.md` for run/use instructions

Runtime documents under `.sparrow/` are for Agent execution and personalization. They are not part of the development-management document system.

### Document Directory

#### Root project documents

- `AGENTS.md`
  The overall project definition, working rules, and document index. Read first.
- `README.md`
  The operator-facing run and usage document.

#### `docs/`

`docs/` is the project management and design space for development documents.

Current and planned structure:

- `docs/plans/`
  Architecture, implementation, and staged development plans.
- `docs/todos/`
  Deferred ideas and work items that are intentionally not being done yet.
- `docs/reviews/`
  Optional future space for design reviews, retrospectives, or implementation audits if needed.

#### Runtime documents

These documents are for Sparrow Agent runtime behavior, not for managing development work:

- `.sparrow/AGENTS.md`
  Runtime operating instructions used by the agent: how it should work in this workspace.
- `.sparrow/SOUL.md`
  Agent persona, tone, and behavioral boundaries used at runtime.
- `.sparrow/USER.md`
  Stable runtime user profile, preferences, and user-specific context.
- `.sparrow/MEMORY.md`
  Long-term runtime memory.
- `.sparrow/memory/`
  Daily runtime memory and short-term memory artifacts.

### Document Responsibilities

- Use `AGENTS.md` for project overall, working rules, and document navigation.
- Use `docs/plans/` for active or authoritative development plans.
- Use `docs/todos/` for backlog items, deferred ideas, and non-immediate development work.
- Do not use runtime documents under `.sparrow/` to manage project development.
- Use runtime documents only for Agent execution context and personalization behavior.
- `.sparrow/AGENTS.md` is for operating instructions.
- `.sparrow/SOUL.md` is for persona, tone, and boundaries.
- `.sparrow/USER.md` is for who the user is.

## Planning Rules

When a new idea appears during development:

- if it affects the current execution path, put it into an active plan under `docs/plans/`
- if it is useful but not for now, record it later in `docs/todos/`
- do not rely on conversation history alone for important project direction

When a new session starts:

- re-read `AGENTS.md`
- identify the relevant detailed document
- continue from documents, not from assumptions about prior chat context

## Current Document Focus

At the moment, the main project-management document area is:

- `docs/plans/`

### Current Active Development Plan

The current active development plan is:

- `docs/plans/2026-03-20-sparrow-agent-next-development-plan.md`

The currently approved execution order is:

1. Make the project genuinely runnable end-to-end through explicit bootstrap and review flow.
2. Improve markdown memory quality and promotion logic.
3. Strengthen ReAct runtime governance and observability.
4. Upgrade consolidation toward compact-ready memory management.
5. Improve thin product shells in CLI and Web.
6. Clean up tool governance and installation workflow.

The immediate next documentation evolution is:

- keep explicit ToDo tracking under `docs/todos/` for deferred work

Until then:

- keep `AGENTS.md` as the stable high-level guide
- keep active implementation direction in `docs/plans/`

## Non-Goals

Do not turn Sparrow Agent into:

- a multi-Agent orchestration system
- a workflow DAG engine
- a plugin marketplace
- a cloud-native runtime platform
- a generic framework for every Agent use case

## Working Rules

- Prefer changes that make the personal Agent kernel stronger, more personal, or more reliable.
- Avoid infrastructure expansion that does not improve the core Agent experience.
- Keep adapters thin; push core behavior into shared runtime code.
- Treat `AGENTS.md` and `docs/` as the development-management document system.
- Treat runtime documents under `.sparrow/` as runtime context only.
- Treat documentation as persistent project memory for AI-driven development.
- Prefer writing down plans and deferred work rather than depending on chat context.
- Configure the project environment from `README.md` before execution, and prefer running all validation inside that environment.
