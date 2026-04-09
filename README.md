![Sparrow Agent logo](assets/branding/final/sparrow-agent-logo.svg)

## Sparrow Agent

Sparrow Agent is a lightweight Python single-agent runtime with:

- a multi-step ReAct loop
- file-backed session storage
- markdown-based persistent context and memory
- a shared runtime for CLI and Web adapters
- a tool registry with file and memory-document tools
- skill loading hooks
- a placeholder MCP adapter
- OpenAI Responses API support
- streaming assistant text in Web and interactive CLI when the model client supports it

### Run

```bash
uv venv sparrow_env
source sparrow_env/bin/activate
uv pip install -e '.[dev]'
python -m apps.cli.main --session-id demo
uvicorn apps.server.main:app --reload
```

All commands should be run inside this project environment after activation.

CLI controls:

- `Enter` sends the current message
- `Esc+Enter` inserts a newline inside the input box
- `Ctrl+T` toggles the thinking panel
- `Ctrl+C` exits the CLI

### OpenAI Configuration

Use either environment variables or a local config file.

Environment variables:

```bash
export OPENAI_API_KEY="sk-..."
export OPENAI_MODEL="gpt-5.2"
export OPENAI_REASONING_EFFORT="medium"
export OPENAI_TIMEOUT_SECONDS="120"
```

Local config file:

```json
{
  "api_key": "sk-...",
  "model": "gpt-5.2",
  "base_url": "",
  "reasoning_effort": "medium",
  "max_output_tokens": 4000,
  "timeout_seconds": 120
}
```

Save it to `data/config/openai.json`.

Reasoning-capable GPT-5.x models can be configured with `OPENAI_REASONING_EFFORT` such as `none`, `low`, `medium`, `high`, and, for some newer models, `xhigh`.

### Workspace Documents

The runtime treats these markdown files under `.sparrow/` as first-class context:

- `.sparrow/AGENTS.md` for operating instructions
- `.sparrow/SOUL.md` for agent persona, tone, and boundaries
- `.sparrow/USER.md` for who the user is, including preferences and stable context
- `.sparrow/MEMORY.md`
- `.sparrow/memory/YYYY-MM-DD.md`

If they do not exist yet, Sparrow Agent initializes them from `templates/runtime/` on first run.

### Storage

Runtime data is stored under `.sparrow/`:

- `.sparrow/sessions/`
- `.sparrow/MEMORY.md`
- `.sparrow/memory/`
- `.sparrow/logs/`

### Runtime Controls

Sparrow Agent uses several runtime controls to keep long tasks bounded:

- configurable ReAct iteration limit
- per-response output token limit from the model client
- session history consolidation into markdown memory
- stored tool-result truncation
- explicit `/stop`
