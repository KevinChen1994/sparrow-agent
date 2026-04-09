from __future__ import annotations

import itertools
import queue
import select
import shutil
import sys
import threading
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, TextIO, TypeVar

from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.filters import Condition, has_focus
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import ConditionalContainer, HSplit, Layout, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import D
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import Box, TextArea

from sparrow_agent.schemas.models import TraceStep, TurnResult

if TYPE_CHECKING:
    from sparrow_agent.core.runtime import AgentRuntime

T = TypeVar("T")

SPINNER_FRAMES = ("|", "/", "-", "\\")
ANSI_RESET = "\033[0m"
BRAND_INK = "\033[38;2;31;42;52m"
BRAND_TEAL = "\033[38;2;46;111;112m"
BRAND_MUTED = "\033[38;2;74;92;104m"
BRAND_SAGE = "\033[38;2;183;196;190m"

EXIT_COMMANDS = {"exit", "quit"}


def run_with_spinner(
    task: Callable[[], T],
    *,
    label: str = "thinking",
    stream: TextIO | None = None,
    interval: float = 0.1,
    delay: float = 0.2,
    enabled: bool | None = None,
    key_handler: Callable[[str], None] | None = None,
    trace_queue: "queue.Queue[str] | None" = None,
    trace_enabled_getter: Callable[[], bool] | None = None,
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
    stdin = sys.stdin
    stdin_tty = bool(getattr(stdin, "isatty", lambda: False)())
    fd = None
    old_attrs = None
    if key_handler is not None and stdin_tty:
        try:
            import termios
            import tty

            fd = stdin.fileno()
            old_attrs = termios.tcgetattr(fd)
            tty.setcbreak(fd)
        except Exception:  # pragma: no cover
            fd = None
            old_attrs = None

    try:
        if not done.wait(delay):
            while not done.is_set():
                if fd is not None and key_handler is not None:
                    try:
                        readable, _, _ = select.select([fd], [], [], 0)
                        if readable:
                            data = stdin.read(1)
                            if data:
                                key_handler(data)
                    except Exception:  # pragma: no cover
                        pass

                if trace_queue is not None and trace_enabled_getter is not None and trace_enabled_getter():
                    while True:
                        try:
                            trace_line = trace_queue.get_nowait()
                        except queue.Empty:
                            break
                        output.write(f"\r{' ' * max(last_width, 1)}\r")
                        output.write(f"trace> {trace_line}\n")
                        output.flush()

                elapsed = time.monotonic() - start
                line = f"agent {next(frame_iter)} {label}... {elapsed:0.1f}s (Ctrl+T thinking)"
                padded = line.ljust(last_width)
                output.write(f"\r{padded}")
                output.flush()
                last_width = max(last_width, len(line))
                done.wait(interval)

            elapsed = time.monotonic() - start
            final_line = f"agent * ready {elapsed:0.1f}s"
            output.write(f"\r{final_line.ljust(last_width)}\n")
            output.flush()
    finally:
        if fd is not None and old_attrs is not None:
            try:
                import termios

                termios.tcsetattr(fd, termios.TCSADRAIN, old_attrs)
            except Exception:  # pragma: no cover
                pass

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
        _style("        ___", BRAND_SAGE, color),
        _style("    ___( o)>", BRAND_SAGE, color),
        _style("   /   ~~~", BRAND_SAGE, color),
        _style("  '---'", BRAND_SAGE, color),
        _style("    ''", BRAND_SAGE, color),
    ]
    wordmark = [
        _style("Sparrow", BRAND_INK, color) + " " + _style("Agent", BRAND_TEAL, color),
        _style("small but complete.", BRAND_MUTED, color),
    ]
    lines = [
        f"{bird[0]}",
        f"{bird[1]}",
        f"{bird[2]}       {wordmark[0]}",
        f"{bird[3]}       {wordmark[1]}",
        f"{bird[4]}",
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


def format_user_turn(message: str) -> str:
    lines = message.splitlines() or [message]
    body = "\n".join(f"  {line}" if line else "  " for line in lines)
    return f"you>\n{body}"


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


def format_turn_block(result: TurnResult) -> str:
    lines = ["sparrow>", format_agent_reply(result.reply)]
    meta = format_turn_meta(result)
    if meta:
        lines.append(f"[{meta}]")
    return "\n".join(lines)


def render_turn(result: TurnResult, *, stream: TextIO | None = None) -> None:
    output = stream or sys.stdout
    output.write(f"{format_turn_block(result)}\n")
    output.flush()


def format_trace_steps_text(steps: list[TraceStep]) -> str:
    if not steps:
        return ""
    lines = ["thinking>"]
    for step in steps:
        suffix = f" ({step.tool_name})" if step.tool_name else ""
        detail = f" - {step.detail}" if step.detail else ""
        lines.append(f"  [{step.index}] {step.phase}: {step.title}{suffix}{detail}")
    return "\n".join(lines)


def render_trace_steps(steps: list[TraceStep], *, stream: TextIO | None = None) -> None:
    output = stream or sys.stdout
    content = format_trace_steps_text(steps)
    if not content:
        return
    output.write(f"{content}\n")
    output.flush()


def supports_interactive_cli() -> bool:
    return bool(getattr(sys.stdin, "isatty", lambda: False)()) and bool(
        getattr(sys.stdout, "isatty", lambda: False)()
    )


class SparrowCLIApp:
    def __init__(self, runtime: AgentRuntime, *, session_id: str) -> None:
        self.runtime = runtime
        self.session_id = session_id
        self.thinking_enabled = False
        self.busy = False
        self.turn_started_at: float | None = None
        self.current_trace_steps: list[TraceStep] = []
        self.last_trace_steps: list[TraceStep] = []
        self.current_streamed_reply = ""
        self._lock = threading.RLock()
        self._transcript_blocks = [
            build_startup_banner(color=False),
            f"session={session_id} | type 'exit' to quit.",
            "Ctrl+T thinking | Enter send | Esc+Enter newline | Ctrl+C exit",
        ]
        self.transcript_area = TextArea(
            text="",
            read_only=True,
            focusable=False,
            wrap_lines=True,
            scrollbar=False,
            style="class:transcript",
            dont_extend_height=True,
        )
        self.trace_area = TextArea(
            text="",
            read_only=True,
            focusable=False,
            wrap_lines=False,
            scrollbar=False,
            style="class:trace",
            dont_extend_height=True,
        )
        self.input_area = TextArea(
            text="",
            multiline=True,
            wrap_lines=True,
            prompt="you> ",
            height=D(min=2, max=5),
            scrollbar=False,
            focus_on_click=True,
            style="class:input",
            accept_handler=self._accept_input,
        )
        self.status_bar = Window(
            content=FormattedTextControl(self._get_status_fragments),
            height=1,
            style="class:status",
        )
        self.application = Application(
            layout=Layout(self._build_layout(), focused_element=self.input_area),
            key_bindings=self._build_key_bindings(),
            style=self._build_style(),
            full_screen=False,
            erase_when_done=False,
            mouse_support=True,
            refresh_interval=0.1,
        )
        self._refresh_transcript()
        self._refresh_trace()

    def run(self) -> None:
        started = self.runtime.start_session(session_id=self.session_id)
        if started.reply:
            self._append_block(format_turn_block(started))
        self.application.run()

    def _build_layout(self) -> HSplit:
        trace_filter = Condition(lambda: self.thinking_enabled and (self.busy or bool(self.last_trace_steps)))
        return HSplit(
            [
                self.transcript_area,
                ConditionalContainer(self.trace_area, filter=trace_filter),
                Window(height=1, char=" ", style="class:gap"),
                Window(
                    content=FormattedTextControl(lambda: [("class:input-label", " message ")]),
                    height=1,
                    style="class:input-label",
                ),
                Box(
                    body=self.input_area,
                    padding_left=1,
                    padding_right=1,
                    padding_top=0,
                    padding_bottom=0,
                    style="class:input-shell",
                ),
                self.status_bar,
            ]
        )

    def _build_key_bindings(self) -> KeyBindings:
        kb = KeyBindings()

        @kb.add("c-c")
        def _exit_app(event) -> None:
            self.application.exit()

        @kb.add("c-d", filter=has_focus(self.input_area))
        def _exit_on_eof(event) -> None:
            if not self.busy and not self.input_area.text.strip():
                self.application.exit()

        @kb.add("c-t")
        def _toggle_thinking(event) -> None:
            self.thinking_enabled = not self.thinking_enabled
            self._refresh_trace()
            self.application.invalidate()

        @kb.add("enter", filter=has_focus(self.input_area))
        def _submit_message(event) -> None:
            if self.busy:
                return
            event.current_buffer.validate_and_handle()

        @kb.add("escape", "enter", filter=has_focus(self.input_area))
        def _insert_newline(event) -> None:
            event.current_buffer.insert_text("\n")

        return kb

    def _build_style(self) -> Style:
        return Style.from_dict(
            {
                "transcript": "#d7dee5",
                "trace": "bg:#11161c #9fb2c1",
                "input-label": "#6d7d87",
                "input-shell": "bg:#151b22",
                "input": "bg:#151b22 #f3f6f8",
                "status": "bg:#1f2a34 #d9e1e8",
                "gap": "bg:default",
            }
        )

    def _accept_input(self, buffer: Buffer) -> bool:
        raw_text = buffer.text.rstrip()
        message = raw_text.strip()
        if not message:
            return False

        buffer.text = ""

        if message.lower() in EXIT_COMMANDS:
            self._append_block("bye")
            self.application.exit()
            return False

        self._append_block(format_user_turn(raw_text))
        self._start_turn(raw_text)
        return False

    def _start_turn(self, user_input: str) -> None:
        with self._lock:
            self.busy = True
            self.turn_started_at = time.monotonic()
            self.current_trace_steps = []
            self.current_streamed_reply = ""
        self._refresh_trace()
        self._refresh_transcript()
        self.application.invalidate()
        thread = threading.Thread(target=self._run_turn, args=(user_input,), daemon=True)
        thread.start()

    def _run_turn(self, user_input: str) -> None:
        try:
            result = self.runtime.run_turn(
                session_id=self.session_id,
                user_input=user_input,
                trace_callback=self._handle_trace_step,
                response_event_callback=self._handle_response_event,
            )
        except BaseException as exc:  # pragma: no cover
            with self._lock:
                self.busy = False
                self.turn_started_at = None
                self.last_trace_steps = list(self.current_trace_steps)
                self.current_streamed_reply = ""
            self._append_block(f"error>\n  {exc}")
            self._refresh_trace()
            self.application.invalidate()
            return

        with self._lock:
            self.busy = False
            self.turn_started_at = None
            self.last_trace_steps = list(result.trace_steps or self.current_trace_steps)
            self.current_streamed_reply = ""
        self._append_block(format_turn_block(result))
        self._refresh_trace()
        self.application.invalidate()

    def _handle_trace_step(self, step: TraceStep) -> None:
        with self._lock:
            self.current_trace_steps.append(step)
        self._refresh_trace()
        self.application.invalidate()

    def _handle_response_event(self, event: str, payload: dict) -> None:
        with self._lock:
            if event == "response.delta":
                delta = payload.get("delta", "")
                if isinstance(delta, str) and delta:
                    self.current_streamed_reply += delta
            elif event == "response.reset":
                self.current_streamed_reply = ""
        self._refresh_transcript()
        self.application.invalidate()

    def _append_block(self, block: str) -> None:
        block = block.strip("\n")
        if not block:
            return
        with self._lock:
            self._transcript_blocks.append(block)
        self._refresh_transcript()
        self.application.invalidate()

    def _refresh_transcript(self) -> None:
        with self._lock:
            blocks = list(self._transcript_blocks)
            if self.busy and self.current_streamed_reply:
                blocks.append("sparrow>\n" + format_agent_reply(self.current_streamed_reply))
            text = "\n\n".join(blocks).rstrip() + "\n"
        self.transcript_area.buffer.set_document(
            Document(text=text, cursor_position=len(text)),
            bypass_readonly=True,
        )

    def _refresh_trace(self) -> None:
        text = self._build_trace_text()
        self.trace_area.buffer.set_document(
            Document(text=text, cursor_position=len(text)),
            bypass_readonly=True,
        )

    def _build_trace_text(self) -> str:
        with self._lock:
            steps = list(self.current_trace_steps if self.busy else self.last_trace_steps)
            busy = self.busy
        if steps:
            return format_trace_steps_text(steps)
        if busy:
            return "thinking>\n  waiting for model response..."
        return ""

    def _get_status_fragments(self) -> list[tuple[str, str]]:
        with self._lock:
            busy = self.busy
            started_at = self.turn_started_at
            thinking_enabled = self.thinking_enabled

        if busy and started_at is not None:
            elapsed = time.monotonic() - started_at
            frame = SPINNER_FRAMES[int(elapsed / 0.1) % len(SPINNER_FRAMES)]
            lead = f" agent {frame} thinking {elapsed:0.1f}s "
        else:
            lead = " agent ready "

        tail = (
            f"Ctrl+T thinking {'ON' if thinking_enabled else 'OFF'}"
            " | Enter send | Esc+Enter newline | Ctrl+C exit"
        )
        return [("class:status", lead), ("class:status", tail)]


def _supports_color(stream: TextIO) -> bool:
    return bool(getattr(stream, "isatty", lambda: False)()) and getattr(stream, "encoding", None) is not None


def _style(text: str, ansi: str, enabled: bool) -> str:
    if not enabled:
        return text
    return f"{ansi}{text}{ANSI_RESET}"
