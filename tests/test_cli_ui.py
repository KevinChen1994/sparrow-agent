from __future__ import annotations

import io
import time

from apps.cli.ui import (
    build_startup_banner,
    format_agent_reply,
    format_turn_meta,
    render_startup_banner,
    render_turn,
    run_with_spinner,
)
from sparrow_agent.schemas.models import LLMResponse, TurnResult


def test_run_with_spinner_renders_progress_for_slow_task() -> None:
    stream = io.StringIO()

    result = run_with_spinner(
        lambda: (time.sleep(0.03), "done")[1],
        stream=stream,
        interval=0.005,
        delay=0.0,
        enabled=True,
    )

    output = stream.getvalue()
    assert result == "done"
    assert "thinking..." in output
    assert "agent * ready" in output


def test_run_with_spinner_skips_animation_for_fast_task() -> None:
    stream = io.StringIO()

    result = run_with_spinner(lambda: "done", stream=stream, delay=0.1, enabled=True)

    assert result == "done"
    assert stream.getvalue() == ""


def test_format_turn_meta_includes_runtime_details() -> None:
    result = TurnResult(
        session_id="demo",
        reply="hello",
        messages=[],
        used_tools=["read_file", "write_memory"],
        iterations=2,
        llm_response=LLMResponse(
            usage={
                "input_tokens": 12,
                "output_tokens": 34,
                "reasoning_tokens": 8,
                "total_tokens": 46,
            }
        ),
    )

    assert format_turn_meta(result) == "steps 2 | tools read_file, write_memory | tokens in 12, out 34, reason 8, total 46"


def test_render_turn_uses_terminal_style_layout() -> None:
    stream = io.StringIO()
    result = TurnResult(session_id="demo", reply="line 1\nline 2", messages=[])

    render_turn(result, stream=stream)

    assert stream.getvalue() == "sparrow>\n  line 1\n  line 2\n"
    assert format_agent_reply("single line") == "  single line"


def test_build_startup_banner_has_wide_and_compact_variants() -> None:
    wide = build_startup_banner(width=80, color=False)
    compact = build_startup_banner(width=40, color=False)

    assert "___( o)>" in wide
    assert "/   ~~~" in wide
    assert "'---'" in wide
    assert "Sparrow Agent" in wide
    assert compact == "Sparrow Agent\nsmall but complete."


def test_render_startup_banner_writes_spacing() -> None:
    stream = io.StringIO()

    render_startup_banner(stream=stream, width=80)

    output = stream.getvalue()
    assert output.endswith("\n\n")
    assert "small but complete." in output
