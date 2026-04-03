# Storage Structure Refactoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate sessions, logs, and memories under `.sparrow/` while keeping application config in `data/config/`.

**Architecture:** Move three path constants (`SESSIONS_DIR`, `MEMORIES_DIR`, `LOGS_DIR`) from `data/` to `.sparrow/`, update `ensure_data_dirs()`, update all test fixtures, update `.gitignore`, update documentation.

**Tech Stack:** Python, pathlib, pytest

---

### Task 1: Update path constants and directory initialization

**Files:**
- Modify: `sparrow_agent/config.py:8-23,59-61`

- [ ] **Step 1: Write the failing test**

No new test file needed. The existing `tests/test_openai_config.py` and others validate paths indirectly. We'll verify by running existing tests after the change.

- [ ] **Step 2: Update path constants in config.py**

Change lines 10-14 from:

```python
DATA_DIR = ROOT_DIR / "data"
SESSIONS_DIR = DATA_DIR / "sessions"
MEMORIES_DIR = DATA_DIR / "memories"
LOGS_DIR = DATA_DIR / "logs"
CONFIG_DIR = DATA_DIR / "config"
```

To:

```python
DATA_DIR = ROOT_DIR / "data"
CONFIG_DIR = DATA_DIR / "config"
```

And after line 23 (`DAILY_MEMORY_DIR = RUNTIME_DIR / "memory"`), the RUNTIME_DIR block becomes:

```python
RUNTIME_DIR = WORKSPACE_ROOT / ".sparrow"
RUNTIME_TEMPLATES_DIR = ROOT_DIR / "templates" / "runtime"
AGENTS_DOC_PATH = RUNTIME_DIR / "AGENTS.md"
SOUL_DOC_PATH = RUNTIME_DIR / "SOUL.md"
USER_DOC_PATH = RUNTIME_DIR / "USER.md"
MEMORY_DOC_PATH = RUNTIME_DIR / "MEMORY.md"
DAILY_MEMORY_DIR = RUNTIME_DIR / "memory"
SESSIONS_DIR = RUNTIME_DIR / "sessions"
MEMORIES_DIR = RUNTIME_DIR / "memories"
LOGS_DIR = RUNTIME_DIR / "logs"
```

- [ ] **Step 3: Update ensure_data_dirs()**

Change:

```python
def ensure_data_dirs() -> None:
    for path in (SESSIONS_DIR, MEMORIES_DIR, LOGS_DIR, CONFIG_DIR, RUNTIME_DIR, DAILY_MEMORY_DIR):
        path.mkdir(parents=True, exist_ok=True)
```

To:

```python
def ensure_data_dirs() -> None:
    for path in (CONFIG_DIR, RUNTIME_DIR, DAILY_MEMORY_DIR, SESSIONS_DIR, MEMORIES_DIR, LOGS_DIR):
        path.mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 4: Run tests to verify**

Run: `pytest -v`
Expected: All tests pass (tests use explicit paths, not config constants)

- [ ] **Step 5: Commit**

```bash
git add sparrow_agent/config.py
git commit -m "refactor: move sessions/logs/memories paths under .sparrow/"
```

---

### Task 2: Update test fixtures

**Files:**
- Modify: `tests/test_file_store.py:24-26`
- Modify: `tests/test_tools.py:23-25`
- Modify: `tests/test_server.py:28-30`
- Modify: `tests/test_runtime.py:27-29`
- Modify: `tests/test_context_loader.py:23-25`

All five test files have a `build_store()` or `build_runtime()` that passes `sessions_dir=tmp_path / "sessions"` etc. Update them to use `.sparrow/` subdirectories.

- [ ] **Step 1: Update test_file_store.py**

Change:

```python
        sessions_dir=tmp_path / "sessions",
        memories_dir=tmp_path / "memories",
        logs_dir=tmp_path / "logs",
```

To:

```python
        sessions_dir=tmp_path / ".sparrow" / "sessions",
        memories_dir=tmp_path / ".sparrow" / "memories",
        logs_dir=tmp_path / ".sparrow" / "logs",
```

- [ ] **Step 2: Update test_tools.py**

Same change as Step 1.

- [ ] **Step 3: Update test_server.py**

Same change as Step 1.

- [ ] **Step 4: Update test_runtime.py**

Same change as Step 1.

- [ ] **Step 5: Update test_context_loader.py**

Same change as Step 1.

- [ ] **Step 6: Run tests to verify**

Run: `pytest -v`
Expected: All tests pass

- [ ] **Step 7: Commit**

```bash
git add tests/
git commit -m "test: update fixtures to use .sparrow/ for sessions/logs/memories"
```

---

### Task 3: Update .gitignore

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Simplify .gitignore**

Replace:

```
data/sessions/*.json
data/logs/*.jsonl
data/memories/*.jsonl
data/memories/profile.json
data/config/openai.json
```

With:

```
data/config/openai.json
```

The `.sparrow/` line already exists and covers all moved directories.

- [ ] **Step 2: Commit**

```bash
git add .gitignore
git commit -m "chore: simplify .gitignore after storage refactor"
```

---

### Task 4: Update documentation

**Files:**
- Modify: `CLAUDE.md:94-99`
- Modify: `README.md:72-74` (storage section)

- [ ] **Step 1: Update CLAUDE.md Storage section**

Change:

```markdown
### Storage

- `data/sessions/`: Session JSON files
- `data/memories/`: Memory storage
- `data/logs/`: Execution logs
- `data/config/`: OpenAI configuration
```

To:

```markdown
### Storage

- `.sparrow/sessions/`: Session JSON files
- `.sparrow/memories/`: Structured memory (facts.jsonl)
- `.sparrow/logs/`: Execution logs
- `.sparrow/memory/`: Daily memory markdown
- `data/config/`: OpenAI configuration
```

- [ ] **Step 2: Update README.md Storage section**

Change lines referencing `data/sessions/`, `data/memories/`, `data/logs/` to `.sparrow/sessions/`, `.sparrow/memories/`, `.sparrow/logs/`.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md README.md
git commit -m "docs: update storage paths in documentation"
```

---

### Task 5: Clean up old data directories

- [ ] **Step 1: Move existing data to new location**

```bash
mv data/sessions .sparrow/ 2>/dev/null; true
mv data/logs .sparrow/ 2>/dev/null; true
mv data/memories .sparrow/ 2>/dev/null; true
```

- [ ] **Step 2: Remove empty data subdirectories**

```bash
rmdir data/sessions data/logs data/memories 2>/dev/null; true
```

- [ ] **Step 3: Verify final structure**

```bash
ls -la .sparrow/
ls -la data/
```

Expected `.sparrow/` contains: `AGENTS.md`, `MEMORY.md`, `SOUL.md`, `USER.md`, `logs/`, `memories/`, `memory/`, `sessions/`
Expected `data/` contains only: `config/`

- [ ] **Step 4: Final test run**

Run: `pytest -v`
Expected: All tests pass
