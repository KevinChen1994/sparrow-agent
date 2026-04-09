from __future__ import annotations

import re
import secrets
from datetime import datetime, timezone


def generate_session_id(prefix: str = "session") -> str:
    normalized_prefix = _normalize_prefix(prefix)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    suffix = secrets.token_hex(4)
    return f"{normalized_prefix}-{timestamp}-{suffix}"


def resolve_session_id(session_id: str | None, *, prefix: str = "session") -> str:
    if session_id is not None:
        candidate = session_id.strip()
        if candidate:
            return candidate
    return generate_session_id(prefix=prefix)


def _normalize_prefix(value: str) -> str:
    lowered = value.strip().lower()
    normalized = re.sub(r"[^a-z0-9-]+", "-", lowered).strip("-")
    return normalized or "session"
