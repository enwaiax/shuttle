"""Additional tests for _execute_command_logic and _truncate (MCP core).

Covers: truncation, multi-node auto-select error, confirm token validation,
warn-level execution, auto-session creation, DB logging, and error tolerance.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shuttle.core.security import (
    CommandGuard,
    ConfirmTokenStore,
    SecurityDecision,
    SecurityLevel,
)
from shuttle.core.session import SessionManager, SSHSession
from shuttle.mcp.tools import MAX_OUTPUT_BYTES, _execute_command_logic, _truncate

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_guard(level: SecurityLevel, message: str = "", rule: str = "test-rule"):
    guard = MagicMock(spec=CommandGuard)
    guard.evaluate = AsyncMock(
        return_value=SecurityDecision(level=level, matched_rule=rule, message=message)
    )
    return guard


def _sm_with_session(
    session: SSHSession,
    stdout: str = "x",
    exit_status: int = 0,
) -> MagicMock:
    mgr = MagicMock(spec=SessionManager)
    mgr.get.return_value = session
    mgr.list_active.return_value = [session]
    mgr.create = AsyncMock(return_value=session)
    mgr.execute = AsyncMock(
        return_value={
            "stdout": stdout,
            "exit_status": exit_status,
            "working_directory": "/",
        }
    )
    return mgr


@asynccontextmanager
async def _noop_db_ctx():
    yield MagicMock()


def _node_repo_factory(db_sess):
    repo = MagicMock()
    _node = MagicMock()
    _node.id = "fake-uuid-0001"
    _node.name = "n1"
    repo.get_by_name = AsyncMock(return_value=_node)
    repo.list_all = AsyncMock(return_value=[])
    repo.update = AsyncMock()
    return repo


# ---------------------------------------------------------------------------
# _truncate
# ---------------------------------------------------------------------------


def test_truncate_short_unchanged() -> None:
    assert _truncate("hello", 100) == "hello"


def test_truncate_appends_marker_when_over_limit() -> None:
    raw = "\u4e00" * 500
    out = _truncate(raw, 10)
    assert "truncated" in out
    assert len(out.encode("utf-8")) <= MAX_OUTPUT_BYTES


# ---------------------------------------------------------------------------
# Node resolution
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_no_node_multi_nodes_error() -> None:
    guard = _make_guard(SecurityLevel.ALLOW)

    repo = MagicMock()
    n1, n2 = MagicMock(), MagicMock()
    repo.list_all = AsyncMock(return_value=[n1, n2])

    out = await _execute_command_logic(
        command="ls",
        node=None,
        timeout=1,
        confirm_token=None,
        bypass_scope=None,
        pool=MagicMock(),
        guard=guard,
        token_store=MagicMock(spec=ConfirmTokenStore),
        session_mgr=MagicMock(spec=SessionManager),
        db_session_ctx=_noop_db_ctx,
        node_repo_factory=lambda _s: repo,
    )
    assert "cannot auto-select" in out


# ---------------------------------------------------------------------------
# Security: CONFIRM / WARN
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_confirm_invalid_token() -> None:
    session = SSHSession(session_id="s1", node_id="n1")
    guard = _make_guard(SecurityLevel.CONFIRM, message="check", rule="r1")
    ts = MagicMock(spec=ConfirmTokenStore)
    ts.validate.return_value = False

    out = await _execute_command_logic(
        command="sudo ls",
        node="n1",
        timeout=1,
        confirm_token="bad",
        bypass_scope=None,
        pool=MagicMock(),
        guard=guard,
        token_store=ts,
        session_mgr=_sm_with_session(session),
        db_session_ctx=_noop_db_ctx,
        node_repo_factory=_node_repo_factory,
    )
    assert "invalid" in out.lower()


@pytest.mark.asyncio
async def test_execute_warn_still_runs_session_execute() -> None:
    session = SSHSession(session_id="s1", node_id="n1")
    guard = _make_guard(SecurityLevel.WARN, message="careful", rule="w1")
    mgr = _sm_with_session(session)

    with patch("shuttle.mcp.tools.logger.warning") as log_warn:
        out = await _execute_command_logic(
            command="curl x",
            node="n1",
            timeout=1,
            confirm_token=None,
            bypass_scope=None,
            pool=MagicMock(),
            guard=guard,
            token_store=MagicMock(spec=ConfirmTokenStore),
            session_mgr=mgr,
            db_session_ctx=_noop_db_ctx,
            node_repo_factory=_node_repo_factory,
        )
    log_warn.assert_called()
    assert out == "x"


# ---------------------------------------------------------------------------
# Auto-session creation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_auto_session_creation_on_pool_node() -> None:
    """When no session exists, auto-create one and execute via session_mgr."""
    new_session = SSHSession(session_id="auto-new", node_id="n1")
    guard = _make_guard(SecurityLevel.ALLOW)

    mgr = MagicMock(spec=SessionManager)
    mgr.list_active.return_value = []
    mgr.create = AsyncMock(return_value=new_session)
    mgr.execute = AsyncMock(
        return_value={"stdout": "hello", "exit_status": 0, "working_directory": "/"}
    )

    out = await _execute_command_logic(
        command="hostname",
        node="n1",
        timeout=1,
        confirm_token=None,
        bypass_scope=None,
        pool=MagicMock(),
        guard=guard,
        token_store=MagicMock(spec=ConfirmTokenStore),
        session_mgr=mgr,
        db_session_ctx=_noop_db_ctx,
        node_repo_factory=_node_repo_factory,
    )
    assert out == "hello"
    mgr.create.assert_awaited_once_with("n1")
    mgr.execute.assert_awaited_once()


# ---------------------------------------------------------------------------
# DB logging — LogRepo.create called after execution
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_persists_command_log_to_db() -> None:
    """After successful execution, LogRepo.create must be called with correct fields."""
    session = SSHSession(session_id="s1", node_id="n1")
    guard = _make_guard(SecurityLevel.ALLOW)
    mgr = _sm_with_session(session, stdout="hello world", exit_status=0)

    mock_log_repo = MagicMock()
    mock_log_repo.create = AsyncMock()

    with patch("shuttle.db.repository.LogRepo", return_value=mock_log_repo):
        await _execute_command_logic(
            command="echo hello",
            node="n1",
            timeout=10,
            confirm_token=None,
            bypass_scope=None,
            pool=MagicMock(),
            guard=guard,
            token_store=MagicMock(spec=ConfirmTokenStore),
            session_mgr=mgr,
            db_session_ctx=_noop_db_ctx,
            node_repo_factory=_node_repo_factory,
        )

    mock_log_repo.create.assert_awaited_once()
    kwargs = mock_log_repo.create.call_args.kwargs
    assert kwargs["node_id"] == "fake-uuid-0001"
    assert kwargs["session_id"] == "s1"
    assert kwargs["command"] == "echo hello"
    assert kwargs["exit_code"] == 0
    assert kwargs["security_level"] == "allow"
    assert kwargs["bypassed"] is False
    assert isinstance(kwargs["duration_ms"], int)
    assert kwargs["duration_ms"] >= 0


@pytest.mark.asyncio
async def test_execute_persists_log_with_confirm_bypassed() -> None:
    """When confirm_token is provided, bypassed=True in the log entry."""
    session = SSHSession(session_id="s1", node_id="n1")
    guard = _make_guard(SecurityLevel.CONFIRM, message="sudo", rule="r1")

    ts = MagicMock(spec=ConfirmTokenStore)
    ts.validate.return_value = True

    mgr = _sm_with_session(session, stdout="root")

    mock_log_repo = MagicMock()
    mock_log_repo.create = AsyncMock()

    with patch("shuttle.db.repository.LogRepo", return_value=mock_log_repo):
        out = await _execute_command_logic(
            command="sudo whoami",
            node="n1",
            timeout=10,
            confirm_token="valid-token",
            bypass_scope=None,
            pool=MagicMock(),
            guard=guard,
            token_store=ts,
            session_mgr=mgr,
            db_session_ctx=_noop_db_ctx,
            node_repo_factory=_node_repo_factory,
        )

    assert out == "root"
    mock_log_repo.create.assert_awaited_once()
    kwargs = mock_log_repo.create.call_args.kwargs
    assert kwargs["bypassed"] is True
    assert kwargs["security_level"] == "confirm"


@pytest.mark.asyncio
async def test_execute_persists_log_with_nonzero_exit_code() -> None:
    """Log entry must record the real exit_code from execute()."""
    session = SSHSession(session_id="s1", node_id="n1")
    guard = _make_guard(SecurityLevel.ALLOW)
    mgr = _sm_with_session(session, stdout="error output", exit_status=1)

    mock_log_repo = MagicMock()
    mock_log_repo.create = AsyncMock()

    with patch("shuttle.db.repository.LogRepo", return_value=mock_log_repo):
        await _execute_command_logic(
            command="false",
            node="n1",
            timeout=10,
            confirm_token=None,
            bypass_scope=None,
            pool=MagicMock(),
            guard=guard,
            token_store=MagicMock(spec=ConfirmTokenStore),
            session_mgr=mgr,
            db_session_ctx=_noop_db_ctx,
            node_repo_factory=_node_repo_factory,
        )

    kwargs = mock_log_repo.create.call_args.kwargs
    assert kwargs["exit_code"] == 1


@pytest.mark.asyncio
async def test_execute_updates_node_last_seen_at() -> None:
    """After execution, node's last_seen_at and status should be updated."""
    session = SSHSession(session_id="s1", node_id="n1")
    guard = _make_guard(SecurityLevel.ALLOW)
    mgr = _sm_with_session(session)

    update_calls = []
    _node = MagicMock()
    _node.id = "fake-uuid-0001"

    def tracking_factory(db_sess):
        repo = MagicMock()
        repo.get_by_name = AsyncMock(return_value=_node)
        repo.list_all = AsyncMock(return_value=[])

        async def _update(*args, **kwargs):
            update_calls.append((args, kwargs))

        repo.update = _update
        return repo

    mock_log_repo = MagicMock()
    mock_log_repo.create = AsyncMock()

    with patch("shuttle.db.repository.LogRepo", return_value=mock_log_repo):
        await _execute_command_logic(
            command="ls",
            node="n1",
            timeout=10,
            confirm_token=None,
            bypass_scope=None,
            pool=MagicMock(),
            guard=guard,
            token_store=MagicMock(spec=ConfirmTokenStore),
            session_mgr=mgr,
            db_session_ctx=_noop_db_ctx,
            node_repo_factory=tracking_factory,
        )

    assert len(update_calls) >= 1
    _, kwargs = update_calls[-1]
    assert kwargs.get("status") == "active"
    assert "last_seen_at" in kwargs


# ---------------------------------------------------------------------------
# DB logging — error tolerance
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_still_returns_stdout_when_db_logging_fails() -> None:
    """If DB logging raises, the command output must still be returned."""
    session = SSHSession(session_id="s1", node_id="n1")
    guard = _make_guard(SecurityLevel.ALLOW)
    mgr = _sm_with_session(session, stdout="important output")

    def _broken_repo_factory(db_sess):
        repo = MagicMock()
        repo.get_by_name = AsyncMock(side_effect=RuntimeError("DB down"))
        repo.list_all = AsyncMock(return_value=[])
        return repo

    out = await _execute_command_logic(
        command="echo test",
        node="n1",
        timeout=10,
        confirm_token=None,
        bypass_scope=None,
        pool=MagicMock(),
        guard=guard,
        token_store=MagicMock(spec=ConfirmTokenStore),
        session_mgr=mgr,
        db_session_ctx=_noop_db_ctx,
        node_repo_factory=_broken_repo_factory,
    )
    assert out == "important output"


@pytest.mark.asyncio
async def test_execute_still_returns_on_session_execute_error() -> None:
    """If session_mgr.execute raises, an error message is returned (not raised)."""
    session = SSHSession(session_id="s1", node_id="n1")
    guard = _make_guard(SecurityLevel.ALLOW)

    mgr = MagicMock(spec=SessionManager)
    mgr.list_active.return_value = [session]
    mgr.execute = AsyncMock(side_effect=ConnectionError("SSH connection lost"))

    out = await _execute_command_logic(
        command="ls",
        node="n1",
        timeout=10,
        confirm_token=None,
        bypass_scope=None,
        pool=MagicMock(),
        guard=guard,
        token_store=MagicMock(spec=ConfirmTokenStore),
        session_mgr=mgr,
        db_session_ctx=_noop_db_ctx,
        node_repo_factory=_node_repo_factory,
    )
    assert "[ERROR]" in out
    assert "SSH connection lost" in out


@pytest.mark.asyncio
async def test_execute_logs_to_db_even_on_command_error() -> None:
    """When execute() raises, exit_code=-1 should still be logged."""
    session = SSHSession(session_id="s1", node_id="n1")
    guard = _make_guard(SecurityLevel.ALLOW)

    mgr = MagicMock(spec=SessionManager)
    mgr.list_active.return_value = [session]
    mgr.execute = AsyncMock(side_effect=TimeoutError("timed out"))

    mock_log_repo = MagicMock()
    mock_log_repo.create = AsyncMock()

    with patch("shuttle.db.repository.LogRepo", return_value=mock_log_repo):
        out = await _execute_command_logic(
            command="sleep 9999",
            node="n1",
            timeout=1,
            confirm_token=None,
            bypass_scope=None,
            pool=MagicMock(),
            guard=guard,
            token_store=MagicMock(spec=ConfirmTokenStore),
            session_mgr=mgr,
            db_session_ctx=_noop_db_ctx,
            node_repo_factory=_node_repo_factory,
        )

    assert "[ERROR]" in out
    mock_log_repo.create.assert_awaited_once()
    kwargs = mock_log_repo.create.call_args.kwargs
    assert kwargs["exit_code"] == -1
