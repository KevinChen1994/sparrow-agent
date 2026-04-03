from __future__ import annotations

import itertools
import shutil
import sys
import threading
import time
from collections.abc import Callable
from typing import TextIO, TypeVar

from sparrow_agent.schemas.models import TurnResult

T = TypeVar("T")

SPINNER_FRAMES = ("|", "/", "-", "\\")
ANSI_RESET = "\033[0m"
BRAND_INK = "\033[38;2;31;42;52m"
BRAND_TEAL = "\033[38;2;46;111;112m"
BRAND_MUTED = "\033[38;2;74;92;104m"
BRAND_SAGE = "\033[38;2;183;196;190m"


def run_with_spinner(
    task: Callable[[], T],
    *,
    label: str = "thinking",
    stream: TextIO | None = None,
    interval: float = 0.1,
    delay: float = 0.2,
    enabled: bool | None = None,
) -> T:
    output = stream or sys.stdout
    should_animate = enabled if enabled is not None else bool(getattr(output, "isatty", lambda: False)())
    if not should_animate:
        return task()

    state: dict[str, T | BaseException | None] = {"result": None, "error": None}
    done = threading.Event()

    def worker() -> None:
        try:
            state["result"] = task()
        except BaseException as exc:  # pragma: no cover
            state["error"] = exc
        finally:
            done.set()

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    start = time.monotonic()
    frame_iter = itertools.cycle(SPINNER_FRAMES)
    last_width = 0

    if not done.wait(delay):
        while not done.is_set():
            elapsed = time.monotonic() - start
            line = f"agent {next(frame_iter)} {label}... {elapsed:0.1f}s"
            padded = line.ljust(last_width)
            output.write(f"\r{padded}")
            output.flush()
            last_width = max(last_width, len(line))
            done.wait(interval)

        elapsed = time.monotonic() - start
        final_line = f"agent * ready {elapsed:0.1f}s"
        output.write(f"\r{final_line.ljust(last_width)}\n")
        output.flush()

    thread.join()

    if isinstance(state["error"], BaseException):
        raise state["error"]

    return state["result"]  # type: ignore[return-value]


def build_startup_banner(*, width: int | None = None, color: bool = False) -> str:
    terminal_width = width if width is not None else shutil.get_terminal_size(fallback=(80, 24)).columns
    if terminal_width < 52:
        title = _style("Sparrow", BRAND_INK, color) + " " + _style("Agent", BRAND_TEAL, color)
        subtitle = _style("small but complete.", BRAND_MUTED, color)
        return "\n".join((title, subtitle))

    bird = [
        _style("   __", BRAND_SAGE, color),
        _style(" __(o )>", BRAND_SAGE, color),
        _style(" \\ <_. )", BRAND_SAGE, color),
        _style("  `---'", BRAND_SAGE, color),
    ]
    wordmark = [
        _style("Sparrow", BRAND_INK, color) + " " + _style("Agent", BRAND_TEAL, color),
        _style("small but complete.", BRAND_MUTED, color),
    ]
    lines = [
        f"{bird[0]}",
        f"{bird[1]}  {wordmark[0]}",
        f"{bird[2]}  {wordmark[1]}",
        f"{bird[3]}",
    ]
    return "\n".join(lines)


def render_startup_banner(*, stream: TextIO | None = None, width: int | None = None) -> None:
    output = stream or sys.stdout
    output.write(build_startup_banner(width=width, color=_supports_color(output)))
    output.write("\n\n")
    output.flush()


def format_agent_reply(reply: str) -> str:
    lines = reply.splitlines() or [reply]
    return "\n".join(f"  {line}" if line else "  " for line in lines)


def format_turn_meta(result: TurnResult) -> str:
    parts: list[str] = []
    if result.iterations:
        parts.append(f"steps {result.iterations}")
    if result.used_tools:
        parts.append("tools " + ", ".join(result.used_tools))

    usage = result.llm_response.usage if result.llm_response is not None else {}
    token_parts: list[str] = []
    if usage.get("input_tokens") is not None:
        token_parts.append(f"in {usage['input_tokens']}")
    if usage.get("output_tokens") is not None:
        token_parts.append(f"out {usage['output_tokens']}")
    if usage.get("reasoning_tokens") is not None:
        token_parts.append(f"reason {usage['reasoning_tokens']}")
    if usage.get("cached_tokens") is not None:
        token_parts.append(f"cached {usage['cached_tokens']}")
    if usage.get("total_tokens") is not None:
        token_parts.append(f"total {usage['total_tokens']}")
    if token_parts:
        parts.append("tokens " + ", ".join(token_parts))

    return " | ".join(parts)


def render_turn(result: TurnResult, *, stream: TextIO | None = None) -> None:
    output = stream or sys.stdout
    output.write("sparrow>\n")
    output.write(f"{format_agent_reply(result.reply)}\n")
    meta = format_turn_meta(result)
    if meta:
        output.write(f"[{meta}]\n")
    output.flush()


def _supports_color(stream: TextIO) -> bool:
    return bool(getattr(stream, "isatty", lambda: False)()) and getattr(stream, "encoding", None) is not None


def _style(text: str, ansi: str, enabled: bool) -> str:
    if not enabled:
        return text
    return f"{ansi}{text}{ANSI_RESET}"
