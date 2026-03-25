"""Tests for SSHSession dataclass and SessionManager."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from shuttle.core.session import (
    PWD_SENTINEL,
    SessionManager,
    SessionStatus,
    SSHSession,
    _parse_sentinel_output,
    _wrap_command,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ssh_result(
    stdout: str = "", stderr: str = "", exit_status: int = 0
) -> MagicMock:
    """Return a mock asyncssh result with the given fields."""
    r = MagicMock()
    r.stdout = stdout
    r.stderr = stderr
    r.exit_status = exit_status
    return r


def make_mock_pool(initial_pwd: str = "/home/testuser") -> MagicMock:
    """Return a mock ConnectionPool whose connections report *initial_pwd*."""
    mock_result = _make_ssh_result(stdout=initial_pwd)

    mock_conn_obj = MagicMock()
    mock_conn_obj.run = AsyncMock(return_value=mock_result)

    pooled_conn = MagicMock()
    pooled_conn.conn = mock_conn_obj

    # connection() must be an async context manager
    mock_pool = MagicMock()
    mock_pool.connection = MagicMock(
        return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=pooled_conn),
            __aexit__=AsyncMock(return_value=False),
        )
    )
    return mock_pool


def _set_pool_result(
    pool: MagicMock,
    stdout: str = "",
    stderr: str = "",
    exit_status: int = 0,
) -> None:
    """Reconfigure *pool* so subsequent commands return the given result."""
    mock_result = _make_ssh_result(
        stdout=stdout, stderr=stderr, exit_status=exit_status
    )
    pooled_conn = MagicMock()
    pooled_conn.conn = MagicMock()
    pooled_conn.conn.run = AsyncMock(return_value=mock_result)
    pool.connection = MagicMock(
        return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=pooled_conn),
            __aexit__=AsyncMock(return_value=False),
        )
    )


# ---------------------------------------------------------------------------
# SSHSession dataclass
# ---------------------------------------------------------------------------


def test_ssh_session_creation():
    session = SSHSession(session_id="abc", node_id="prod-web")
    assert session.session_id == "abc"
    assert session.node_id == "prod-web"
    assert session.working_directory == "~"
    assert session.status == SessionStatus.ACTIVE
    assert session.bypass_patterns == set()
    assert session.env_vars == {}


def test_ssh_session_bypass_patterns():
    session = SSHSession(session_id="s1", node_id="node-1")
    session.bypass_patterns.add(r"rm -rf")
    session.bypass_patterns.add(r"sudo")
    assert r"rm -rf" in session.bypass_patterns
    assert r"sudo" in session.bypass_patterns
    assert len(session.bypass_patterns) == 2


def test_ssh_session_bypass_patterns_independence():
    """Two sessions should have independent bypass_patterns sets."""
    s1 = SSHSession(session_id="s1", node_id="n")
    s2 = SSHSession(session_id="s2", node_id="n")
    s1.bypass_patterns.add("rm")
    assert "rm" not in s2.bypass_patterns


def test_ssh_session_env_vars():
    session = SSHSession(session_id="s1", node_id="n", env_vars={"FOO": "bar"})
    assert session.env_vars["FOO"] == "bar"


# ---------------------------------------------------------------------------
# _wrap_command
# ---------------------------------------------------------------------------


def test_wrap_command_simple():
    result = _wrap_command("ls -la", "/home/user")
    assert result == f"cd /home/user && ls -la; echo {PWD_SENTINEL}; pwd"


def test_wrap_command_quotes_directory_with_spaces():
    result = _wrap_command("ls", "/home/my user")
    # shlex.quote should wrap the directory in single quotes
    assert "'/home/my user'" in result
    assert PWD_SENTINEL in result


def test_wrap_command_quotes_directory_with_special_chars():
    result = _wrap_command("echo hi", "/tmp/foo$bar")
    # shlex.quote should protect the $ sign
    assert "'/tmp/foo$bar'" in result


def test_wrap_command_includes_sentinel():
    result = _wrap_command("pwd", "/tmp")
    assert f"echo {PWD_SENTINEL}" in result
    assert result.endswith("; pwd")


def test_wrap_command_plain_path_not_quoted():
    """Plain paths without special chars should still be safe."""
    result = _wrap_command("cat file.txt", "/var/log")
    # shlex.quote leaves plain paths unquoted
    assert "/var/log" in result


# ---------------------------------------------------------------------------
# _parse_sentinel_output
# ---------------------------------------------------------------------------


def test_parse_sentinel_output_normal():
    raw = f"hello world\n{PWD_SENTINEL}\n/home/user\n"
    stdout, pwd = _parse_sentinel_output(raw)
    assert stdout == "hello world"
    assert pwd == "/home/user"


def test_parse_sentinel_output_no_sentinel():
    raw = "some output without sentinel"
    stdout, pwd = _parse_sentinel_output(raw)
    assert stdout == raw
    assert pwd == ""


def test_parse_sentinel_output_empty_pwd():
    raw = f"output\n{PWD_SENTINEL}\n"
    stdout, pwd = _parse_sentinel_output(raw)
    assert stdout == "output"
    assert pwd == ""


# ---------------------------------------------------------------------------
# SessionManager.create
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_session_manager_create_returns_session():
    pool = make_mock_pool(initial_pwd="/home/testuser")
    manager = SessionManager(pool=pool)

    session = await manager.create("node-1")

    assert session.node_id == "node-1"
    assert session.working_directory == "/home/testuser"
    assert session.status == SessionStatus.ACTIVE
    assert len(session.session_id) == 36  # UUID4 format


@pytest.mark.asyncio
async def test_session_manager_create_stores_session():
    pool = make_mock_pool()
    manager = SessionManager(pool=pool)

    session = await manager.create("node-1")

    assert manager.get(session.session_id) is session


@pytest.mark.asyncio
async def test_session_manager_create_multiple_sessions():
    pool = make_mock_pool()
    manager = SessionManager(pool=pool)

    s1 = await manager.create("node-1")
    s2 = await manager.create("node-1")

    assert s1.session_id != s2.session_id
    assert len(manager.list_active()) == 2


# ---------------------------------------------------------------------------
# SessionManager.execute
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_updates_working_directory():
    pool = make_mock_pool()
    manager = SessionManager(pool=pool)

    session = await manager.create("node-1")

    _set_pool_result(pool, stdout=f"file.txt\n{PWD_SENTINEL}\n/tmp\n")

    result = await manager.execute(session.session_id, "cd /tmp && ls")

    assert result["working_directory"] == "/tmp"
    assert session.working_directory == "/tmp"


@pytest.mark.asyncio
async def test_execute_raises_for_unknown_session():
    pool = make_mock_pool()
    manager = SessionManager(pool=pool)

    with pytest.raises(KeyError, match="not found"):
        await manager.execute("nonexistent-session-id", "ls")


@pytest.mark.asyncio
async def test_execute_returns_stdout():
    pool = make_mock_pool()
    manager = SessionManager(pool=pool)

    session = await manager.create("node-1")

    _set_pool_result(pool, stdout=f"hello\n{PWD_SENTINEL}\n/home/testuser\n")

    result = await manager.execute(session.session_id, "echo hello")

    assert result["stdout"] == "hello"


# ---------------------------------------------------------------------------
# SessionManager.close / get / list_active
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_close_removes_session():
    pool = make_mock_pool()
    manager = SessionManager(pool=pool)

    session = await manager.create("node-1")
    session_id = session.session_id

    await manager.close(session_id)

    assert manager.get(session_id) is None
    assert len(manager.list_active()) == 0


@pytest.mark.asyncio
async def test_close_nonexistent_session_noop():
    pool = make_mock_pool()
    manager = SessionManager(pool=pool)

    # Should not raise
    await manager.close("does-not-exist")


@pytest.mark.asyncio
async def test_list_active_returns_only_active():
    pool = make_mock_pool()
    manager = SessionManager(pool=pool)

    s1 = await manager.create("node-1")
    s2 = await manager.create("node-1")

    await manager.close(s1.session_id)

    active = manager.list_active()
    assert len(active) == 1
    assert active[0].session_id == s2.session_id


@pytest.mark.asyncio
async def test_execute_truncates_huge_stdout(monkeypatch):
    monkeypatch.setattr("shuttle.core.session.MAX_OUTPUT_BYTES", 8)
    pool = make_mock_pool()
    manager = SessionManager(pool=pool)
    session = await manager.create("node-1")

    big = "a" * 20
    _set_pool_result(pool, stdout=f"{big}\n{PWD_SENTINEL}\n/home/x\n")

    result = await manager.execute(session.session_id, "cmd")
    assert len(result["stdout"].encode()) <= 8


@pytest.mark.asyncio
async def test_execute_keeps_working_directory_when_sentinel_has_no_pwd():
    pool = make_mock_pool()
    manager = SessionManager(pool=pool)
    session = await manager.create("node-1")
    prev = session.working_directory

    _set_pool_result(pool, stdout=f"out\n{PWD_SENTINEL}\n")

    await manager.execute(session.session_id, "cmd")
    assert session.working_directory == prev


@pytest.mark.asyncio
async def test_persist_hooks_noop_without_db_factory():
    pool = make_mock_pool()
    manager = SessionManager(pool=pool, db_session_factory=None)
    session = await manager.create("node-1")
    await manager.execute(session.session_id, "echo")
    await manager.close(session.session_id)


# ---------------------------------------------------------------------------
# exit_status / stderr / _run_on_node contract
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_returns_real_exit_status():
    """execute() must propagate the real exit_status from asyncssh, not hardcode 0."""
    pool = make_mock_pool()
    manager = SessionManager(pool=pool)
    session = await manager.create("node-1")

    _set_pool_result(
        pool,
        stdout=f"not found\n{PWD_SENTINEL}\n/home/testuser\n",
        exit_status=127,
    )

    result = await manager.execute(session.session_id, "nonexistent_cmd")
    assert result["exit_status"] == 127


@pytest.mark.asyncio
async def test_execute_returns_zero_exit_status_on_success():
    pool = make_mock_pool()
    manager = SessionManager(pool=pool)
    session = await manager.create("node-1")

    _set_pool_result(
        pool,
        stdout=f"ok\n{PWD_SENTINEL}\n/home/testuser\n",
        exit_status=0,
    )

    result = await manager.execute(session.session_id, "echo ok")
    assert result["exit_status"] == 0


@pytest.mark.asyncio
async def test_execute_returns_stderr():
    """execute() must include stderr from the remote command."""
    pool = make_mock_pool()
    manager = SessionManager(pool=pool)
    session = await manager.create("node-1")

    _set_pool_result(
        pool,
        stdout=f"\n{PWD_SENTINEL}\n/home/testuser\n",
        stderr="Permission denied",
        exit_status=1,
    )

    result = await manager.execute(session.session_id, "cat /etc/shadow")
    assert result["stderr"] == "Permission denied"
    assert result["exit_status"] == 1


@pytest.mark.asyncio
async def test_execute_returns_empty_stderr_on_success():
    pool = make_mock_pool()
    manager = SessionManager(pool=pool)
    session = await manager.create("node-1")

    _set_pool_result(
        pool,
        stdout=f"hello\n{PWD_SENTINEL}\n/home/testuser\n",
        stderr="",
        exit_status=0,
    )

    result = await manager.execute(session.session_id, "echo hello")
    assert result["stderr"] == ""


@pytest.mark.asyncio
async def test_run_on_node_returns_dict_contract():
    """_run_on_node must return a dict with stdout, stderr, exit_status keys."""
    pool = make_mock_pool()
    manager = SessionManager(pool=pool)

    _set_pool_result(pool, stdout="out", stderr="err", exit_status=42)

    result = await manager._run_on_node("node-1", "test_cmd")
    assert isinstance(result, dict)
    assert set(result.keys()) == {"stdout", "stderr", "exit_status"}
    assert result["stdout"] == "out"
    assert result["stderr"] == "err"
    assert result["exit_status"] == 42


@pytest.mark.asyncio
async def test_run_on_node_defaults_empty_on_none():
    """_run_on_node returns empty strings when asyncssh gives None."""
    mock_result = MagicMock()
    mock_result.stdout = None
    mock_result.stderr = None
    mock_result.exit_status = 0

    pooled_conn = MagicMock()
    pooled_conn.conn = MagicMock()
    pooled_conn.conn.run = AsyncMock(return_value=mock_result)

    pool = MagicMock()
    pool.connection = MagicMock(
        return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=pooled_conn),
            __aexit__=AsyncMock(return_value=False),
        )
    )
    manager = SessionManager(pool=pool)

    result = await manager._run_on_node("node-1", "cmd")
    assert result["stdout"] == ""
    assert result["stderr"] == ""


@pytest.mark.asyncio
async def test_execute_result_has_all_keys():
    """execute() return dict must have stdout, stderr, exit_status, working_directory."""
    pool = make_mock_pool()
    manager = SessionManager(pool=pool)
    session = await manager.create("node-1")

    _set_pool_result(
        pool,
        stdout=f"data\n{PWD_SENTINEL}\n/home/testuser\n",
        stderr="warn",
        exit_status=2,
    )

    result = await manager.execute(session.session_id, "cmd")
    assert set(result.keys()) == {
        "stdout",
        "stderr",
        "exit_status",
        "working_directory",
    }
    assert result["stdout"] == "data"
    assert result["stderr"] == "warn"
    assert result["exit_status"] == 2
    assert result["working_directory"] == "/home/testuser"
