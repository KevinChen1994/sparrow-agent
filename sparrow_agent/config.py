from __future__ import annotations

import json
import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = ROOT_DIR
DATA_DIR = ROOT_DIR / "data"
SESSIONS_DIR = DATA_DIR / "sessions"
MEMORIES_DIR = DATA_DIR / "memories"
LOGS_DIR = DATA_DIR / "logs"
CONFIG_DIR = DATA_DIR / "config"
OPENAI_CONFIG_PATH = CONFIG_DIR / "openai.json"

RUNTIME_DIR = WORKSPACE_ROOT / ".sparrow"
RUNTIME_TEMPLATES_DIR = ROOT_DIR / "templates" / "runtime"
AGENTS_DOC_PATH = RUNTIME_DIR / "AGENTS.md"
SOUL_DOC_PATH = RUNTIME_DIR / "SOUL.md"
USER_DOC_PATH = RUNTIME_DIR / "USER.md"
MEMORY_DOC_PATH = RUNTIME_DIR / "MEMORY.md"
DAILY_MEMORY_DIR = RUNTIME_DIR / "memory"

DEFAULT_AGENTS_DOC = """# AGENTS

## Core Rules
- Operate as Sparrow Agent, a local-first personal assistant.
- Prefer accurate, direct, and concise execution.
- Use tools when they materially improve the answer or complete work.
- Do not auto-modify this file during normal execution.
"""

DEFAULT_SOUL_DOC = """# SOUL

## Style
- Be pragmatic, clear, and task-oriented.
- Prefer concrete actions over abstract discussion.
- Stay calm and explicit about tradeoffs.
"""

DEFAULT_USER_DOC = """# USER

## Profile
- Preferred name: Unknown

## Preferences
- Language: Chinese
- Communication: Concise and direct
"""

DEFAULT_MEMORY_DOC = """# MEMORY

## Important Notes
- No long-term memory captured yet.
"""


def ensure_data_dirs() -> None:
    for path in (SESSIONS_DIR, MEMORIES_DIR, LOGS_DIR, CONFIG_DIR, RUNTIME_DIR, DAILY_MEMORY_DIR):
        path.mkdir(parents=True, exist_ok=True)


def load_openai_settings() -> dict[str, str]:
    file_settings: dict[str, str] = {}
    if OPENAI_CONFIG_PATH.exists():
        file_settings = json.loads(OPENAI_CONFIG_PATH.read_text(encoding="utf-8"))

    settings = {
        "api_key": os.getenv("OPENAI_API_KEY", file_settings.get("api_key", "")),
        "model": os.getenv("OPENAI_MODEL", file_settings.get("model", "gpt-5.2")),
        "base_url": os.getenv("OPENAI_BASE_URL", file_settings.get("base_url", "")),
        "reasoning_effort": os.getenv("OPENAI_REASONING_EFFORT", file_settings.get("reasoning_effort", "")),
        "max_output_tokens": os.getenv("OPENAI_MAX_OUTPUT_TOKENS", str(file_settings.get("max_output_tokens", ""))),
    }
    return {key: value for key, value in settings.items() if value}
