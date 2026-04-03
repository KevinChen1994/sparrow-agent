# Storage Structure Refactoring

**Date:** 2026-04-03
**Status:** Approved

## Overview

Refactor storage structure to consolidate agent-related data under `.sparrow/` while keeping application configuration in `data/config/`.

## Current Structure

```
data/
├── sessions/          # Session JSON files
├── logs/              # Daily JSONL logs
├── memories/          # facts.jsonl (structured memories)
└── config/            # openai.json

.sparrow/
├── AGENTS.md, SOUL.md, USER.md, MEMORY.md
└── memory/            # Daily memory markdown files
```

**Problem:** Agent state is split between `data/` and `.sparrow/`, creating conceptual confusion.

## Target Structure

```
.sparrow/
├── AGENTS.md, SOUL.md, USER.md, MEMORY.md
├── memory/            # Daily memory markdown
├── memories/          # facts.jsonl (moved from data/)
├── sessions/          # Session JSON (moved from data/)
└── logs/              # Daily JSONL logs (moved from data/)

data/
└── config/            # Application configuration (openai.json)
```

**Rationale:**
- `.sparrow/` = complete agent workspace (all agent state and memory)
- `data/config/` = application-level configuration (API keys, model settings)
- Clear separation: agent state vs application config

## Implementation

### 1. Update Path Constants

**File:** `sparrow_agent/config.py`

Change path definitions:

```python
# Keep in data/
DATA_DIR = ROOT_DIR / "data"
CONFIG_DIR = DATA_DIR / "config"
OPENAI_CONFIG_PATH = CONFIG_DIR / "openai.json"

# Move to .sparrow/
RUNTIME_DIR = WORKSPACE_ROOT / ".sparrow"
SESSIONS_DIR = RUNTIME_DIR / "sessions"
MEMORIES_DIR = RUNTIME_DIR / "memories"
LOGS_DIR = RUNTIME_DIR / "logs"
DAILY_MEMORY_DIR = RUNTIME_DIR / "memory"
```

### 2. Update Directory Initialization

**File:** `sparrow_agent/config.py`

Update `ensure_data_dirs()` to create new structure:

```python
def ensure_data_dirs() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    MEMORIES_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    DAILY_MEMORY_DIR.mkdir(parents=True, exist_ok=True)
```

### 3. Update .gitignore

**File:** `.gitignore`

Simplify to:

```
data/config/openai.json
.sparrow/
```

### 4. Manual Migration

Users need to manually move existing data:

```bash
mv data/sessions .sparrow/
mv data/logs .sparrow/
mv data/memories .sparrow/
```

## Files to Modify

1. `sparrow_agent/config.py` - path constants and `ensure_data_dirs()`
2. `.gitignore` - simplify entries
3. No other files need changes (all use constants from `config.py`)

## Testing

- Run existing tests to verify path changes work correctly
- Manually test CLI and server with new structure
- Verify logs, sessions, and memories are written to correct locations

## Rollout

No migration code needed - this is a breaking change for the (non-existent) user base. Users will need to manually move their data directories.
