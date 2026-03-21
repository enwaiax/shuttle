"""Shuttle CLI — full implementation with node, config, and web sub-commands."""

from __future__ import annotations

import asyncio
import secrets
from pathlib import Path

import typer

app = typer.Typer(
    name="shuttle",
    help="Shuttle — Secure SSH gateway for AI assistants",
    add_completion=False,
)
node_app = typer.Typer(help="Manage SSH nodes")
config_app = typer.Typer(help="Manage Shuttle configuration")

app.add_typer(node_app, name="node")
app.add_typer(config_app, name="config")


# ── Root command ──────────────────────────────────────────────────────────────

def _version_callback(value: bool) -> None:
    if value:
        from shuttle import __version__
        typer.echo(f"Shuttle v{__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="Show version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """Start the Shuttle MCP server (default command)."""
    if ctx.invoked_subcommand is None:
        async def _run() -> None:
            from shuttle.mcp.server import create_mcp_server
            mcp = await create_mcp_server()
            await mcp.run_async()

        asyncio.run(_run())


# ── Serve command ─────────────────────────────────────────────────────────────

@app.command("serve")
def serve(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Bind address"),
    port: int = typer.Option(9876, "--port", "-p", help="Bind port"),
    db_url: str | None = typer.Option(None, "--db-url", help="Database URL override"),
) -> None:
    """Start Shuttle in service mode (MCP + Web on single HTTP server)."""
    import uvicorn

    from shuttle.core.config import ShuttleConfig

    config = ShuttleConfig()
    config.shuttle_dir.mkdir(parents=True, exist_ok=True)

    # Load or generate API token
    token_path = config.shuttle_dir / "web_token"
    if token_path.exists():
        api_token = token_path.read_text().strip()
    else:
        api_token = secrets.token_urlsafe(32)
        token_path.write_text(api_token)
        token_path.chmod(0o600)

    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text

    console = Console()
    info = Text()
    info.append("  MCP endpoint  ", style="dim")
    info.append(f"http://{host}:{port}/mcp\n", style="cyan")
    info.append("  Web panel     ", style="dim")
    info.append(f"http://{host}:{port}\n", style="cyan")
    info.append("  API token     ", style="dim")
    info.append(api_token, style="green bold")
    console.print(Panel(info, title="[bold green]Shuttle[/bold green]", subtitle=f"http://{host}:{port}", border_style="green"))

    import logging

    async def _run():
        from shuttle.mcp.server import create_service_app

        service_app = await create_service_app(
            host=host, port=port, api_token=api_token, db_url=db_url,
        )

        # Suppress noisy shutdown tracebacks. uvicorn/starlette/anyio emit
        # ERROR-level CancelledError tracebacks during graceful shutdown —
        # normal behavior but alarming to users. We filter them out.
        class _ShutdownFilter(logging.Filter):
            shutting_down = False
            def filter(self, record: logging.LogRecord) -> bool:
                msg = record.getMessage()
                if "Shutting down" in msg:
                    self.shutting_down = True
                if self.shutting_down and record.levelno >= logging.ERROR:
                    return False
                return True

        logging.getLogger("uvicorn.error").addFilter(_ShutdownFilter())

        uvi_config = uvicorn.Config(
            service_app,
            host=host,
            port=port,
            log_level="info",
            timeout_graceful_shutdown=3,
        )
        server = uvicorn.Server(uvi_config)
        await server.serve()

    try:
        asyncio.run(_run())
    except (KeyboardInterrupt, SystemExit):
        pass

    typer.echo("Shuttle stopped.")


# ── Node commands ─────────────────────────────────────────────────────────────

@node_app.command("add")
def node_add() -> None:
    """Add a new SSH node interactively."""
    name = typer.prompt("Node name")
    host = typer.prompt("Host")
    username = typer.prompt("Username")
    port = typer.prompt("Port", default="22")
    password = typer.prompt("Password (leave empty to use key file)", default="", hide_input=True)

    if password:
        auth_type = "password"
        credential = password
    else:
        key_path = typer.prompt("Private key file path")
        credential = Path(key_path).expanduser().read_text()
        auth_type = "key"

    async def _add() -> None:
        from shuttle.core.config import ShuttleConfig
        from shuttle.core.credentials import CredentialManager
        from shuttle.db.engine import create_db_engine, create_session_factory, init_db
        from shuttle.db.repository import NodeRepo

        config = ShuttleConfig()
        config.shuttle_dir.mkdir(parents=True, exist_ok=True)

        db_url = config.db_url
        if ":///" in db_url and "~" in db_url:
            db_url = db_url.replace("~", str(Path.home()))

        engine = create_db_engine(db_url)
        await init_db(engine)
        session_factory = create_session_factory(engine)

        cred_mgr = CredentialManager(config.shuttle_dir)
        encrypted = cred_mgr.encrypt(credential)

        async with session_factory() as session:
            repo = NodeRepo(session)
            existing = await repo.get_by_name(name)
            if existing is not None:
                typer.secho(f"Node '{name}' already exists.", fg=typer.colors.RED, err=True)
                raise typer.Exit(1)
            await repo.create(
                name=name,
                host=host,
                port=int(port),
                username=username,
                auth_type=auth_type,
                encrypted_credential=encrypted,
            )

        await engine.dispose()

    asyncio.run(_add())
    typer.secho(f"Node '{name}' added successfully.", fg=typer.colors.GREEN)


@node_app.command("list")
def node_list() -> None:
    """List all SSH nodes."""
    async def _list() -> None:
        from shuttle.core.config import ShuttleConfig
        from shuttle.db.engine import create_db_engine, create_session_factory, init_db
        from shuttle.db.repository import NodeRepo

        config = ShuttleConfig()
        db_url = config.db_url
        if ":///" in db_url and "~" in db_url:
            db_url = db_url.replace("~", str(Path.home()))

        engine = create_db_engine(db_url)
        await init_db(engine)
        session_factory = create_session_factory(engine)

        async with session_factory() as session:
            repo = NodeRepo(session)
            nodes = await repo.list_all()

        await engine.dispose()

        if not nodes:
            typer.echo("No nodes configured. Use 'shuttle node add' to add one.")
            return

        from rich.console import Console
        from rich.table import Table

        table = Table(border_style="dim", show_lines=False, padding=(0, 1))
        table.add_column("Node", style="bold")
        table.add_column("Host", style="cyan")
        table.add_column("Port", justify="right")
        table.add_column("User", style="dim")

        for node in nodes:
            dot = "[green]●[/green]" if node.status == "active" else "[red]●[/red]" if node.status == "error" else "[dim]○[/dim]"
            table.add_row(f"{dot} {node.name}", node.host, str(node.port), node.username)

        Console().print(table)

    asyncio.run(_list())


@node_app.command("edit")
def node_edit(name: str = typer.Argument(..., help="Node name to edit")) -> None:
    """Edit an existing SSH node interactively."""
    async def _edit() -> None:
        from shuttle.core.config import ShuttleConfig
        from shuttle.core.credentials import CredentialManager
        from shuttle.db.engine import create_db_engine, create_session_factory, init_db
        from shuttle.db.repository import NodeRepo

        config = ShuttleConfig()
        config.shuttle_dir.mkdir(parents=True, exist_ok=True)

        db_url = config.db_url
        if ":///" in db_url and "~" in db_url:
            db_url = db_url.replace("~", str(Path.home()))

        engine = create_db_engine(db_url)
        await init_db(engine)
        session_factory = create_session_factory(engine)

        async with session_factory() as session:
            repo = NodeRepo(session)
            node = await repo.get_by_name(name)
            if node is None:
                typer.secho(f"Node '{name}' not found.", fg=typer.colors.RED, err=True)
                await engine.dispose()
                raise typer.Exit(1)

            new_host = typer.prompt("Host", default=node.host)
            new_port = typer.prompt("Port", default=str(node.port))
            new_username = typer.prompt("Username", default=node.username)
            change_cred = typer.confirm("Change credentials?", default=False)

            updates: dict = {
                "host": new_host,
                "port": int(new_port),
                "username": new_username,
            }

            if change_cred:
                new_auth = typer.prompt("Auth type (password/key)", default=node.auth_type)
                if new_auth == "password":
                    credential = typer.prompt("Password", hide_input=True)
                else:
                    key_path = typer.prompt("Path to private key file")
                    credential = Path(key_path).expanduser().read_text()
                cred_mgr = CredentialManager(config.shuttle_dir)
                updates["auth_type"] = new_auth
                updates["encrypted_credential"] = cred_mgr.encrypt(credential)

            await repo.update(node.id, **updates)

        await engine.dispose()

    asyncio.run(_edit())
    typer.secho(f"Node '{name}' updated successfully.", fg=typer.colors.GREEN)


@node_app.command("test")
def node_test(name: str = typer.Argument(..., help="Node name to test")) -> None:
    """Test SSH connectivity to a node."""
    async def _test() -> None:
        from shuttle.core.config import ShuttleConfig
        from shuttle.core.credentials import CredentialManager
        from shuttle.core.proxy import NodeConnectInfo, connect_ssh
        from shuttle.db.engine import create_db_engine, create_session_factory, init_db
        from shuttle.db.repository import NodeRepo

        config = ShuttleConfig()
        db_url = config.db_url
        if ":///" in db_url and "~" in db_url:
            db_url = db_url.replace("~", str(Path.home()))

        engine = create_db_engine(db_url)
        await init_db(engine)
        session_factory = create_session_factory(engine)

        async with session_factory() as session:
            repo = NodeRepo(session)
            node = await repo.get_by_name(name)
            if node is None:
                typer.secho(f"Node '{name}' not found.", fg=typer.colors.RED, err=True)
                await engine.dispose()
                raise typer.Exit(1)

            cred_mgr = CredentialManager(config.shuttle_dir)
            password = None
            private_key = None
            if node.encrypted_credential:
                decrypted = cred_mgr.decrypt(node.encrypted_credential)
                if node.auth_type == "key":
                    private_key = decrypted
                else:
                    password = decrypted

            # Resolve jump host if configured
            jump_host_info = None
            if node.jump_host_id:
                jh_node = await repo.get_by_id(node.jump_host_id)
                if jh_node and jh_node.encrypted_credential:
                    jh_dec = cred_mgr.decrypt(jh_node.encrypted_credential)
                    jump_host_info = NodeConnectInfo(
                        node_id=jh_node.name,
                        hostname=jh_node.host,
                        port=jh_node.port,
                        username=jh_node.username,
                        password=jh_dec if jh_node.auth_type == "password" else None,
                        private_key=jh_dec if jh_node.auth_type == "key" else None,
                    )

            info = NodeConnectInfo(
                node_id=node.name,
                hostname=node.host,
                port=node.port,
                username=node.username,
                password=password,
                private_key=private_key,
                jump_host=jump_host_info,
            )

            typer.echo(f"Testing connection to '{name}' ({node.host}:{node.port})...")
            try:
                conn = await connect_ssh(info)
                result = await conn.run("echo ok", check=True)
                conn.close()
                output = result.stdout.strip()
                if output == "ok":
                    typer.secho(f"Connection successful: {name}", fg=typer.colors.GREEN)
                    await repo.update(node.id, status="active")
                else:
                    typer.secho(f"Unexpected output: {output!r}", fg=typer.colors.YELLOW)
            except Exception as exc:
                typer.secho(f"Connection failed: {exc}", fg=typer.colors.RED, err=True)
                await repo.update(node.id, status="error")
                await engine.dispose()
                raise typer.Exit(1)

        await engine.dispose()

    asyncio.run(_test())


@node_app.command("remove")
def node_remove(
    name: str = typer.Argument(..., help="Node name to remove"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Remove an SSH node."""
    if not yes:
        confirmed = typer.confirm(f"Remove node '{name}'?")
        if not confirmed:
            typer.echo("Aborted.")
            raise typer.Exit()

    async def _remove() -> None:
        from shuttle.core.config import ShuttleConfig
        from shuttle.db.engine import create_db_engine, create_session_factory, init_db
        from shuttle.db.repository import NodeRepo

        config = ShuttleConfig()
        db_url = config.db_url
        if ":///" in db_url and "~" in db_url:
            db_url = db_url.replace("~", str(Path.home()))

        engine = create_db_engine(db_url)
        await init_db(engine)
        session_factory = create_session_factory(engine)

        async with session_factory() as session:
            repo = NodeRepo(session)
            node = await repo.get_by_name(name)
            if node is None:
                typer.secho(f"Node '{name}' not found.", fg=typer.colors.RED, err=True)
                await engine.dispose()
                raise typer.Exit(1)
            deleted = await repo.delete(node.id)

        await engine.dispose()
        if deleted:
            typer.secho(f"Node '{name}' removed.", fg=typer.colors.GREEN)
        else:
            typer.secho(f"Failed to remove node '{name}'.", fg=typer.colors.RED, err=True)

    asyncio.run(_remove())


# ── Config commands ───────────────────────────────────────────────────────────

@config_app.command("show")
def config_show() -> None:
    """Show current Shuttle configuration."""
    from shuttle import __version__
    from shuttle.core.config import ShuttleConfig

    from rich.console import Console
    from rich.table import Table

    config = ShuttleConfig()
    table = Table(title="Shuttle Configuration", border_style="dim", show_header=False, padding=(0, 2))
    table.add_column("Key", style="dim")
    table.add_column("Value", style="bold")

    table.add_row("Version", f"[green]{__version__}[/green]")
    table.add_row("Shuttle dir", str(config.shuttle_dir))
    table.add_row("Database", config.db_url)
    table.add_row("Web", f"{config.web_host}:{config.web_port}")
    table.add_row("Pool max total", str(config.pool_max_total))
    table.add_row("Pool max/node", str(config.pool_max_per_node))
    table.add_row("Pool idle timeout", f"{config.pool_idle_timeout}s")
    table.add_row("Pool max lifetime", f"{config.pool_max_lifetime}s")

    Console().print(table)
