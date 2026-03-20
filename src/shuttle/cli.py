"""Shuttle CLI — stub for initial scaffold."""

import typer

app = typer.Typer(
    name="shuttle",
    help="Shuttle — Secure SSH gateway for AI assistants",
    add_completion=False,
)

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """Start MCP server (default)."""
    if ctx.invoked_subcommand is None:
        typer.echo("Shuttle MCP server (not yet implemented)")
