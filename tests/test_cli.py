"""CLI tests — Typer entrypoints with mocks (no real SSH / long-running servers)."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from shuttle.cli import app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def cli_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("SHUTTLE_DB_URL", f"sqlite+aiosqlite:///{tmp_path / 'cli.db'}")
    return tmp_path


def test_cli_version_shows_shuttle(runner: CliRunner) -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "Shuttle" in result.stdout


def test_cli_default_starts_mcp_server(runner: CliRunner) -> None:
    mock_mcp = MagicMock()
    mock_mcp.run_async = AsyncMock()
    with patch(
        "shuttle.mcp.server.create_mcp_server", new_callable=AsyncMock
    ) as create:
        create.return_value = mock_mcp
        result = runner.invoke(app, [])
    assert result.exit_code == 0
    create.assert_awaited_once()
    mock_mcp.run_async.assert_awaited_once()


def test_cli_serve_starts_uvicorn(runner: CliRunner, cli_home: Path) -> None:
    mock_server = MagicMock()
    mock_server.serve = AsyncMock()

    async def _fake_service_app(**_kw):
        return MagicMock()

    with (
        patch(
            "shuttle.mcp.server.create_service_app",
            new_callable=AsyncMock,
            side_effect=_fake_service_app,
        ),
        patch("uvicorn.Config") as mock_cfg,
        patch("uvicorn.Server", return_value=mock_server) as mock_srv_cls,
    ):
        result = runner.invoke(app, ["serve", "--host", "127.0.0.1", "--port", "18888"])

    assert result.exit_code == 0
    assert "Shuttle stopped." in result.stdout
    mock_cfg.assert_called_once()
    mock_srv_cls.assert_called_once()
    mock_server.serve.assert_awaited_once()


def test_cli_serve_keyboard_interrupt_still_prints_stopped(
    runner: CliRunner, cli_home: Path
) -> None:
    def boom(_coro):
        raise KeyboardInterrupt()

    with (
        patch("shuttle.cli.asyncio.run", side_effect=boom),
    ):
        result = runner.invoke(app, ["serve", "--port", "19999"])
    assert result.exit_code == 0
    assert "Shuttle stopped." in result.stdout


def test_cli_serve_reuses_existing_token_file(
    runner: CliRunner, cli_home: Path
) -> None:
    shuttle_dir = cli_home / ".shuttle"
    shuttle_dir.mkdir(parents=True)
    tok_path = shuttle_dir / "web_token"
    tok_path.write_text("existing-token")
    mock_server = MagicMock()
    mock_server.serve = AsyncMock()
    with (
        patch("shuttle.mcp.server.create_service_app", new_callable=AsyncMock),
        patch("uvicorn.Config"),
        patch("uvicorn.Server", return_value=mock_server),
    ):
        result = runner.invoke(app, ["serve", "--port", "17777"])
    assert result.exit_code == 0
    assert tok_path.read_text().strip() == "existing-token"


def test_cli_node_add_non_interactive_password(
    runner: CliRunner, cli_home: Path
) -> None:
    mock_conn = MagicMock()
    mock_conn.run = AsyncMock(return_value=MagicMock(stdout="ok\n"))
    mock_conn.close = MagicMock()
    with patch(
        "shuttle.core.proxy.connect_ssh",
        new_callable=AsyncMock,
        return_value=mock_conn,
    ):
        result = runner.invoke(
            app,
            [
                "node",
                "add",
                "-n",
                "cli-node",
                "-H",
                "10.0.0.5",
                "-u",
                "root",
                "--password",
                "pw",
            ],
        )
    assert result.exit_code == 0
    assert "cli-node" in result.stdout


def test_cli_node_add_duplicate_exits_error(runner: CliRunner, cli_home: Path) -> None:
    with patch("shuttle.core.proxy.connect_ssh", new_callable=AsyncMock):
        runner.invoke(
            app,
            [
                "node",
                "add",
                "-n",
                "dup",
                "-H",
                "10.0.0.1",
                "-u",
                "u",
                "--password",
                "p",
            ],
        )
    r2 = runner.invoke(
        app,
        [
            "node",
            "add",
            "-n",
            "dup",
            "-H",
            "10.0.0.2",
            "-u",
            "u",
            "--password",
            "p",
        ],
    )
    assert r2.exit_code == 1
    assert "already exists" in r2.stdout or "already exists" in r2.stderr


def test_cli_node_add_key_file_missing(runner: CliRunner, cli_home: Path) -> None:
    result = runner.invoke(
        app,
        [
            "node",
            "add",
            "-n",
            "k",
            "-H",
            "10.0.0.1",
            "-u",
            "u",
            "-k",
            str(cli_home / "nope.pem"),
        ],
    )
    assert result.exit_code == 1
    assert "not found" in result.stdout or "not found" in result.stderr


def test_cli_node_list_empty(runner: CliRunner, cli_home: Path) -> None:
    result = runner.invoke(app, ["node", "list"])
    assert result.exit_code == 0
    assert "No nodes" in result.stdout


def test_cli_node_list_with_nodes(runner: CliRunner, cli_home: Path) -> None:
    with patch("shuttle.core.proxy.connect_ssh", new_callable=AsyncMock):
        runner.invoke(
            app,
            [
                "node",
                "add",
                "-n",
                "listed",
                "-H",
                "10.1.1.1",
                "-u",
                "u",
                "--password",
                "p",
            ],
        )
    result = runner.invoke(app, ["node", "list"])
    assert result.exit_code == 0
    assert "listed" in result.stdout


def test_cli_node_remove_yes(runner: CliRunner, cli_home: Path) -> None:
    with patch("shuttle.core.proxy.connect_ssh", new_callable=AsyncMock):
        runner.invoke(
            app,
            [
                "node",
                "add",
                "-n",
                "rm-me",
                "-H",
                "10.2.2.2",
                "-u",
                "u",
                "--password",
                "p",
            ],
        )
    result = runner.invoke(app, ["node", "remove", "rm-me", "--yes"])
    assert result.exit_code == 0
    assert "removed" in result.stdout


def test_cli_node_remove_aborted_without_yes(runner: CliRunner, cli_home: Path) -> None:
    with patch("shuttle.core.proxy.connect_ssh", new_callable=AsyncMock):
        runner.invoke(
            app,
            [
                "node",
                "add",
                "-n",
                "keep",
                "-H",
                "10.3.3.3",
                "-u",
                "u",
                "--password",
                "p",
            ],
        )
    with patch("shuttle.cli.typer.confirm", return_value=False):
        result = runner.invoke(app, ["node", "remove", "keep"])
    assert result.exit_code != 0 or "Aborted" in result.stdout


def test_cli_node_test_not_found(runner: CliRunner, cli_home: Path) -> None:
    result = runner.invoke(app, ["node", "test", "ghost"])
    assert result.exit_code == 1


def test_cli_node_test_success(runner: CliRunner, cli_home: Path) -> None:
    with patch("shuttle.core.proxy.connect_ssh", new_callable=AsyncMock):
        runner.invoke(
            app,
            [
                "node",
                "add",
                "-n",
                "live",
                "-H",
                "10.4.4.4",
                "-u",
                "u",
                "--password",
                "p",
            ],
        )
    mock_conn = MagicMock()
    mock_conn.run = AsyncMock(return_value=MagicMock(stdout="ok\n"))
    mock_conn.close = MagicMock()
    with patch(
        "shuttle.core.proxy.connect_ssh",
        new_callable=AsyncMock,
        return_value=mock_conn,
    ):
        result = runner.invoke(app, ["node", "test", "live"])
    assert result.exit_code == 0
    assert "connected" in result.stdout


def test_cli_node_test_bad_output(runner: CliRunner, cli_home: Path) -> None:
    with patch("shuttle.core.proxy.connect_ssh", new_callable=AsyncMock):
        runner.invoke(
            app,
            [
                "node",
                "add",
                "-n",
                "odd",
                "-H",
                "10.5.5.5",
                "-u",
                "u",
                "--password",
                "p",
            ],
        )
    mock_conn = MagicMock()
    mock_conn.run = AsyncMock(return_value=MagicMock(stdout="weird\n"))
    mock_conn.close = MagicMock()
    with patch(
        "shuttle.core.proxy.connect_ssh",
        new_callable=AsyncMock,
        return_value=mock_conn,
    ):
        result = runner.invoke(app, ["node", "test", "odd"])
    assert result.exit_code == 0
    assert "unexpected" in result.stdout.lower() or "Unexpected" in result.stdout


def test_cli_node_test_connection_fails(runner: CliRunner, cli_home: Path) -> None:
    with patch("shuttle.core.proxy.connect_ssh", new_callable=AsyncMock):
        runner.invoke(
            app,
            [
                "node",
                "add",
                "-n",
                "bad",
                "-H",
                "10.6.6.6",
                "-u",
                "u",
                "--password",
                "p",
            ],
        )
    with patch(
        "shuttle.core.proxy.connect_ssh",
        new_callable=AsyncMock,
        side_effect=OSError("refused"),
    ):
        result = runner.invoke(app, ["node", "test", "bad"])
    assert result.exit_code == 1


def test_cli_config_show(runner: CliRunner, cli_home: Path) -> None:
    result = runner.invoke(app, ["config", "show"])
    assert result.exit_code == 0
    assert "Shuttle Configuration" in result.stdout or "Database" in result.stdout


def test_cli_node_edit_updates_node(
    runner: CliRunner, cli_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with patch("shuttle.core.proxy.connect_ssh", new_callable=AsyncMock):
        runner.invoke(
            app,
            [
                "node",
                "add",
                "-n",
                "edit-me",
                "-H",
                "10.7.7.7",
                "-u",
                "u",
                "--password",
                "p",
            ],
        )

    monkeypatch.setattr(
        "shuttle.cli.typer.prompt", lambda *a, **k: k.get("default", "")
    )
    monkeypatch.setattr("shuttle.cli.typer.confirm", lambda *a, **k: False)

    result = runner.invoke(app, ["node", "edit", "edit-me"])
    assert result.exit_code == 0
    assert "updated" in result.stdout


def test_cli_node_edit_not_found(runner: CliRunner, cli_home: Path) -> None:
    result = runner.invoke(app, ["node", "edit", "missing"])
    assert result.exit_code == 1


def test_cli_node_add_offline_still_creates(runner: CliRunner, cli_home: Path) -> None:
    with patch(
        "shuttle.core.proxy.connect_ssh",
        new_callable=AsyncMock,
        side_effect=OSError("down"),
    ):
        result = runner.invoke(
            app,
            [
                "node",
                "add",
                "-n",
                "offline",
                "-H",
                "10.8.8.8",
                "-u",
                "u",
                "--password",
                "p",
            ],
        )
    assert result.exit_code == 0
    assert "offline" in result.stdout.lower() or "offline" in result.stdout


def test_cli_node_add_connection_unexpected_stdout(
    runner: CliRunner, cli_home: Path
) -> None:
    mock_conn = MagicMock()
    mock_conn.run = AsyncMock(return_value=MagicMock(stdout="not-ok\n"))
    mock_conn.close = MagicMock()
    with patch(
        "shuttle.core.proxy.connect_ssh",
        new_callable=AsyncMock,
        return_value=mock_conn,
    ):
        result = runner.invoke(
            app,
            [
                "node",
                "add",
                "-n",
                "weird-out",
                "-H",
                "10.9.9.9",
                "-u",
                "u",
                "--password",
                "p",
            ],
        )
    assert result.exit_code == 0


def test_cli_node_remove_not_found(runner: CliRunner, cli_home: Path) -> None:
    result = runner.invoke(app, ["node", "remove", "nope", "--yes"])
    assert result.exit_code == 1


def test_cli_node_edit_change_credentials(
    runner: CliRunner, cli_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with patch("shuttle.core.proxy.connect_ssh", new_callable=AsyncMock):
        runner.invoke(
            app,
            [
                "node",
                "add",
                "-n",
                "cred-node",
                "-H",
                "10.10.10.10",
                "-u",
                "u",
                "--password",
                "old",
            ],
        )

    prompts: list[tuple[str, ...]] = []

    def fake_prompt(msg, default=None, hide_input=False, **_):
        prompts.append((str(msg),))
        if "Host" in str(msg):
            return "10.0.0.1"
        if "Port" in str(msg):
            return "22"
        if "Username" in str(msg):
            return "root"
        if "Auth type" in str(msg):
            return "password"
        if hide_input:
            return "newsecret"
        if "Path to private key" in str(msg):
            return "/tmp/k"
        return default or ""

    monkeypatch.setattr("shuttle.cli.typer.prompt", fake_prompt)
    monkeypatch.setattr("shuttle.cli.typer.confirm", lambda *a, **k: True)

    result = runner.invoke(app, ["node", "edit", "cred-node"])
    assert result.exit_code == 0


def test_cli_node_test_with_jump_host(
    runner: CliRunner, cli_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exercise jump host resolution branch in node_test."""
    asyncio.run(_seed_jump_nodes(cli_home))
    mock_conn = MagicMock()
    mock_conn.run = AsyncMock(return_value=MagicMock(stdout="ok\n"))
    mock_conn.close = MagicMock()
    with patch(
        "shuttle.core.proxy.connect_ssh",
        new_callable=AsyncMock,
        return_value=mock_conn,
    ):
        result = runner.invoke(app, ["node", "test", "target-j"])
    assert result.exit_code == 0


async def _seed_jump_nodes(cli_home: Path) -> None:
    from shuttle.core.config import ShuttleConfig
    from shuttle.core.credentials import CredentialManager
    from shuttle.db.engine import create_db_engine, create_session_factory, init_db
    from shuttle.db.repository import NodeRepo

    cfg = ShuttleConfig()
    cfg.shuttle_dir.mkdir(parents=True, exist_ok=True)
    url = cfg.db_url.replace("~", str(cli_home))
    eng = create_db_engine(url)
    await init_db(eng)
    sf = create_session_factory(eng)
    cm = CredentialManager(cfg.shuttle_dir)
    enc = cm.encrypt("pw")
    async with sf() as s:
        repo = NodeRepo(s)
        j = await repo.create(
            name="jump-j",
            host="10.20.0.1",
            username="root",
            auth_type="password",
            encrypted_credential=enc,
        )
        await repo.create(
            name="target-j",
            host="10.20.0.2",
            username="root",
            auth_type="password",
            encrypted_credential=enc,
            jump_host_id=j.id,
        )
    await eng.dispose()
