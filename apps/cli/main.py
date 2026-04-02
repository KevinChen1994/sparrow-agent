from __future__ import annotations

import typer

from sparrow_agent.core.runtime import AgentRuntime

app = typer.Typer(add_completion=False)


@app.command()
def main(session_id: str = typer.Option("default", help="Session identifier.")) -> None:
    runtime = AgentRuntime()
    typer.echo(f"Sparrow Agent CLI session={session_id}. Type 'exit' to quit.")
    started = runtime.start_session(session_id=session_id)
    if started.reply:
        typer.echo(f"agent> {started.reply}")
    while True:
        user_input = typer.prompt("you")
        if user_input.strip().lower() in {"exit", "quit"}:
            typer.echo("bye")
            break
        result = runtime.run_turn(session_id=session_id, user_input=user_input)
        typer.echo(f"agent> {result.reply}")


if __name__ == "__main__":
    app()
