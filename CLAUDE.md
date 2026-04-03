# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Sparrow Agent is a lightweight Python single-agent runtime with a multi-step ReAct loop, file-backed session storage, and markdown-based memory. It provides a shared agent kernel used by both CLI and Web adapters.

**Key principle**: This is an agent-kernel project, not a framework. Keep the core runtime strong and adapters thin.

## Setup

Always work inside the project environment:

```bash
uv venv sparrow_env
source sparrow_env/bin/activate
uv pip install -e .[dev]
```

All commands must run inside this activated environment.

## Common Commands

```bash
# Run CLI
python -m apps.cli.main --session-id demo

# Run Web Server
uvicorn apps.server.main:app --reload

# Run tests
pytest

# Run specific test
pytest tests/test_specific.py::test_function_name
```

## OpenAI Configuration

Configure via environment variables or `data/config/openai.json`:

```bash
export OPENAI_API_KEY="sk-..."
export OPENAI_MODEL="gpt-5.2"
export OPENAI_REASONING_EFFORT="medium"
```

## Architecture

### Core Layers

1. **Agent Kernel** (`sparrow_agent/core/`): The main runtime logic
   - `runtime.py`: `AgentRuntime` orchestrates everything - session management, context loading, ReAct loop execution, consolidation
   - `react_loop.py`: Multi-step ReAct loop with tool execution
   - `bootstrap.py`: Session initialization and welcome prompts
   - `consolidator.py`: Converts session history to markdown memory
   - `context_loader.py`: Loads runtime documents from `.sparrow/`
   - `halt_policy.py`: Iteration and token limits

2. **Product Shell** (`apps/`): Thin adapters around the shared kernel
   - `cli/main.py`: Typer-based CLI entry point
   - `server/main.py`: FastAPI server with `/api/chat` and `/api/session/{id}` endpoints
   - `web/`: Static web UI files

3. **LLM Integration** (`sparrow_agent/llm/`):
   - `openai_client.py`: OpenAI Responses API client with reasoning effort support
   - `base.py`: `ModelClient` interface

4. **Tools** (`sparrow_agent/tools/`):
   - `registry.py`: Tool registration and execution
   - `filesystem.py`: Read, write, edit, list directory tools
   - `memory_docs.py`: Memory document manipulation tools

5. **Capabilities** (`sparrow_agent/capabilities/`):
   - `mcp.py`: Model Context Protocol adapter (placeholder)
   - `skills.py`: Skill loading and resolution

### Data Flow

User input → `AgentRuntime.run_turn()` → Load context from `.sparrow/` → Recall memories → Resolve skills → Execute explicit commands OR run ReAct loop → Consolidate to memory → Persist session → Return response

### Runtime Documents

The agent loads these markdown files from `.sparrow/` as first-class context:
- `AGENTS.md`: Operating instructions
- `SOUL.md`: Agent personality
- `USER.md`: User profile
- `MEMORY.md`: Long-term memory index
- `memory/YYYY-MM-DD.md`: Daily memory logs

Initialized from `templates/runtime/` on first run.

### Storage

- `data/sessions/`: Session JSON files
- `data/memories/`: Memory storage
- `data/logs/`: Execution logs
- `data/config/`: OpenAI configuration

## Development Guidelines

### Read AGENTS.md First

Before making changes, read `AGENTS.md` - it defines project positioning, architectural identity, and working rules. It serves as the development document directory.

### Keep Adapters Thin

CLI and Web adapters in `apps/` should be minimal. Push shared logic into `sparrow_agent/core/runtime.py`.

### Prefer Depth Over Breadth

Focus on strengthening the single-agent kernel rather than adding new features:
- Improve ReAct loop reliability
- Enhance memory consolidation quality
- Add tool governance (confirmation, mutation boundaries)
- Strengthen personalization flows

### Document-Driven Development

This project uses AI-first development. Important decisions and plans must be written into documents under `docs/` so future sessions can recover state. Don't rely on chat memory alone.

Reading order for development work:
1. `AGENTS.md` (project definition and document directory)
2. Relevant document in `docs/`
3. `README.md` (run/usage instructions)

### Non-Goals

Do not turn this into:
- A multi-agent orchestration system
- A workflow DAG engine
- A plugin marketplace
- A cloud-native platform
- A generic framework

## Key Implementation Details

### ReAct Loop

The loop in `react_loop.py` runs until:
- Model returns content without tool calls
- Iteration limit reached (default 40)
- Halt policy triggers

Each iteration: generate response → check halt → execute tools → append observations → repeat

### Session Consolidation

`SessionConsolidator` converts recent session history into markdown memory entries, with configurable memory window and tool result truncation.

### Tool Execution

Tools are registered in `ToolRegistry` and executed with `RuntimeContext`. All filesystem tools are workspace-scoped to prevent path traversal.

### Skill Resolution

Skills are resolved from `RuntimeContext` before each turn. Active skills are included in the context passed to the model.
