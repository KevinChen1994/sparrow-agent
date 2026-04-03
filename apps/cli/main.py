from __future__ import annotations

import queue

import typer

from apps.cli.ui import render_startup_banner, render_trace_steps, render_turn, run_with_spinner
from sparrow_agent.core.runtime import AgentRuntime
from sparrow_agent.schemas.models import TraceStep

app = typer.Typer(add_completion=False)


@app.command()
def main(session_id: str = typer.Option("default", help="Session identifier.")) -> None:
    runtime = AgentRuntime()
    thinking_enabled = False
    trace_queue: "queue.Queue[str]" = queue.Queue()
    render_startup_banner()
    typer.echo(f"session={session_id} | type 'exit' to quit.")
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
        if user_input.strip().lower() in {"exit", "quit"}:
            typer.echo("bye")
            break
        result = run_with_spinner(
            lambda: runtime.run_turn(session_id=session_id, user_input=user_input, trace_callback=enqueue_trace),
            label="thinking",
            key_handler=handle_keypress,
            trace_queue=trace_queue,
            trace_enabled_getter=lambda: thinking_enabled,
        )
        render_turn(result)
        if thinking_enabled:
            render_trace_steps(result.trace_steps)


if __name__ == "__main__":
    app()
