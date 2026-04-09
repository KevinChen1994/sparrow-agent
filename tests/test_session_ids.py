from __future__ import annotations

import re

from sparrow_agent.session_ids import generate_session_id, resolve_session_id


def test_generate_session_id_is_safe_and_prefixed() -> None:
    session_id = generate_session_id(prefix="CLI Session")

    assert re.fullmatch(r"cli-session-\d{8}-\d{6}-[0-9a-f]{8}", session_id)


def test_resolve_session_id_preserves_explicit_value() -> None:
    assert resolve_session_id("demo-session", prefix="cli") == "demo-session"


def test_resolve_session_id_generates_when_missing() -> None:
    session_id = resolve_session_id(None, prefix="cli")

    assert session_id.startswith("cli-")
    assert session_id != "default"


def test_resolve_session_id_generates_when_blank() -> None:
    session_id = resolve_session_id("   ", prefix="cli")

    assert session_id.startswith("cli-")
