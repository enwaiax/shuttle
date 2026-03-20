"""Tests for SSHSession dataclass and SessionManager."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from shuttle.core.session import (
    PWD_SENTINEL,
    SSHSession,
    SessionManager,
    SessionStatus,
    _parse_sentinel_output,
    _wrap_command,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_mock_pool(initial_pwd: str = "/home/testuser") -> MagicMock:
    """Return a mock ConnectionPool whose connections report *initial_pwd*."""
    mock_result = MagicMock()
    mock_result.stdout = initial_pwd

    mock_conn_obj = MagicMock()
    mock_conn_obj.run = AsyncMock(return_value=mock_result)

    pooled_conn = MagicMock()
    pooled_conn.conn = mock_conn_obj

    # connection() must be an async context manager
    mock_pool = MagicMock()
    mock_pool.connection = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=pooled_conn),
        __aexit__=AsyncMock(return_value=False),
    ))
    return mock_pool


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

    # Now simulate an execute that changes directory
    execute_result = MagicMock()
    execute_result.stdout = f"file.txt\n{PWD_SENTINEL}\n/tmp\n"

    pooled_conn = MagicMock()
    pooled_conn.conn.run = AsyncMock(return_value=execute_result)

    pool.connection = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=pooled_conn),
        __aexit__=AsyncMock(return_value=False),
    ))

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

    execute_result = MagicMock()
    execute_result.stdout = f"hello\n{PWD_SENTINEL}\n/home/testuser\n"

    pooled_conn = MagicMock()
    pooled_conn.conn.run = AsyncMock(return_value=execute_result)

    pool.connection = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=pooled_conn),
        __aexit__=AsyncMock(return_value=False),
    ))

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
