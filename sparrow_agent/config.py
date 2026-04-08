from __future__ import annotations

import json
import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = ROOT_DIR
DATA_DIR = ROOT_DIR / "data"
CONFIG_DIR = DATA_DIR / "config"
OPENAI_CONFIG_PATH = CONFIG_DIR / "openai.json"

RUNTIME_DIR = WORKSPACE_ROOT / ".sparrow"
RUNTIME_TEMPLATES_DIR = ROOT_DIR / "templates" / "runtime"
AGENTS_DOC_PATH = RUNTIME_DIR / "AGENTS.md"
SOUL_DOC_PATH = RUNTIME_DIR / "SOUL.md"
USER_DOC_PATH = RUNTIME_DIR / "USER.md"
MEMORY_DOC_PATH = RUNTIME_DIR / "MEMORY.md"
DAILY_MEMORY_DIR = RUNTIME_DIR / "memory"
SESSIONS_DIR = RUNTIME_DIR / "sessions"
LOGS_DIR = RUNTIME_DIR / "logs"

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

## Purpose
- This file stores who the user is: profile, preferences, and stable user context.
- Only write information about the user here.

## Profile
- Name: Not provided yet.
- Language: (preferred language)

## Preferences
- Communication style: Not provided yet.
- Things to avoid: Not provided yet.

## Stable Context
- Primary uses: Not provided yet.
- Long-term context: Not provided yet.
"""

DEFAULT_MEMORY_DOC = """# MEMORY

## Important Notes
- No long-term memory captured yet.
"""


def ensure_data_dirs() -> None:
    for path in (CONFIG_DIR, RUNTIME_DIR, DAILY_MEMORY_DIR, SESSIONS_DIR, LOGS_DIR):
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
        "timeout_seconds": os.getenv("OPENAI_TIMEOUT_SECONDS", str(file_settings.get("timeout_seconds", ""))),
    }
    return {key: value for key, value in settings.items() if value}
