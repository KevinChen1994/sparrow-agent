from __future__ import annotations

import queue
import sys

import typer

from apps.cli.ui import (
    EXIT_COMMANDS,
    SparrowCLIApp,
    render_startup_banner,
    render_trace_steps,
    render_turn,
    run_with_spinner,
    supports_interactive_cli,
)
from sparrow_agent.core.runtime import AgentRuntime
from sparrow_agent.session_ids import resolve_session_id
from sparrow_agent.schemas.models import TraceStep

app = typer.Typer(add_completion=False)


@app.command()
def main(
    session_id: str | None = typer.Option(
        None,
        "--session-id",
        help="Session identifier. Leave unset to start a new random session.",
    )
) -> None:
    resolved_session_id = resolve_session_id(session_id, prefix="cli")
    runtime = AgentRuntime()
    if supports_interactive_cli():
        SparrowCLIApp(runtime, session_id=resolved_session_id).run()
        return

    _run_basic_cli(runtime, session_id=resolved_session_id)


def _run_basic_cli(runtime: AgentRuntime, *, session_id: str) -> None:
    thinking_enabled = False
    trace_queue: "queue.Queue[str]" = queue.Queue()
    render_startup_banner()
    typer.echo(f"session={session_id} | type 'exit' to quit.")
    if sys.stdin.isatty():
        typer.echo("thinking=OFF | press Ctrl+T while model is thinking to toggle.")
    started = runtime.start_session(session_id=session_id)
    if started.reply:
        render_turn(started)

    def enqueue_trace(step: TraceStep) -> None:
        detail = f" - {step.detail}" if step.detail else ""
        trace_queue.put(f"[{step.index}] {step.phase}: {step.title}{detail}")

    def toggle_thinking() -> bool:
        nonlocal thinking_enabled
        thinking_enabled = not thinking_enabled
        typer.echo(f"\nthinking={'ON' if thinking_enabled else 'OFF'}")
        return thinking_enabled

    def handle_keypress(key: str) -> None:
        if key == "\x14":  # Ctrl+T
            toggle_thinking()

    while True:
        user_input = typer.prompt("you")
        if user_input.strip().lower() in EXIT_COMMANDS:
            typer.echo("bye")
            break
        result = run_with_spinner(
            lambda: runtime.run_turn(session_id=session_id, user_input=user_input, trace_callback=enqueue_trace),
            label="thinking",
            key_handler=handle_keypress if sys.stdin.isatty() else None,
            trace_queue=trace_queue,
            trace_enabled_getter=lambda: thinking_enabled,
        )
        render_turn(result)
        if thinking_enabled:
            render_trace_steps(result.trace_steps)


if __name__ == "__main__":
    app()
