from __future__ import annotations

import typer

from apps.cli.ui import render_startup_banner, render_turn, run_with_spinner
from sparrow_agent.core.runtime import AgentRuntime

app = typer.Typer(add_completion=False)


@app.command()
def main(session_id: str = typer.Option("default", help="Session identifier.")) -> None:
    runtime = AgentRuntime()
    render_startup_banner()
    typer.echo(f"session={session_id} | type 'exit' to quit.")
    started = runtime.start_session(session_id=session_id)
    if started.reply:
        render_turn(started)
    while True:
        user_input = typer.prompt("you")
        if user_input.strip().lower() in {"exit", "quit"}:
            typer.echo("bye")
            break
        result = run_with_spinner(
            lambda: runtime.run_turn(session_id=session_id, user_input=user_input),
            label="thinking",
        )
        render_turn(result)


if __name__ == "__main__":
    app()
