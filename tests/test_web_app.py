from __future__ import annotations

from pathlib import Path


def test_web_uses_session_storage_for_generated_session_id() -> None:
    html = (Path(__file__).resolve().parents[1] / "apps" / "web" / "index.html").read_text(encoding="utf-8")

    assert "sessionStorage" in html
    assert 'const sessionId = "web-demo";' not in html
    assert "buildSessionId" in html
