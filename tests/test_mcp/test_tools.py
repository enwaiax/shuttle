"""Tests for shuttle.mcp.tools — _execute_command_logic unit tests."""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest

from shuttle.core.security import (
    CommandGuard,
    ConfirmTokenStore,
    SecurityDecision,
    SecurityLevel,
)
from shuttle.core.session import SSHSession, SessionManager
from shuttle.mcp.tools import _execute_command_logic


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_guard(level: SecurityLevel, message: str = "", rule: str = "test-rule"):
    """Return a CommandGuard mock that always returns the given decision."""
    guard = MagicMock(spec=CommandGuard)
    guard.evaluate.return_value = SecurityDecision(
        level=level, matched_rule=rule, message=message
    )
    # Expose _rules for bypass_scope logic (empty list for most tests)
    guard._rules = []
    return guard


def _make_token_store():
    return MagicMock(spec=ConfirmTokenStore)


def _make_session_mgr(session: SSHSession | None = None, execute_result=None):
    mgr = MagicMock(spec=SessionManager)
    mgr.get.return_value = session
    if execute_result is not None:
        mgr.execute = AsyncMock(return_value=execute_result)
    else:
        mgr.execute = AsyncMock(return_value={
            "stdout": "ok",
            "exit_status": 0,
            "working_directory": "/home/user",
        })
    mgr.list_active.return_value = []
    return mgr


@asynccontextmanager
async def _noop_db_session():
    yield MagicMock()


def _noop_node_repo_factory(db_sess):
    repo = MagicMock()
    repo.list_all = AsyncMock(return_value=[])
    return repo


def _single_node_repo_factory(db_sess):
    """Returns a repo mock with exactly one node named 'mynode'."""
    node = MagicMock()
    node.name = "mynode"
    node.host = "10.0.0.1"
    node.port = 22
    node.username = "root"
    node.status = "active"
    repo = MagicMock()
    repo.list_all = AsyncMock(return_value=[node])
    return repo


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_allowed_command_executes():
    """When guard returns ALLOW, the command should execute via session_mgr."""
    session = SSHSession(session_id="s1", node_id="node1")
    guard = _make_guard(SecurityLevel.ALLOW)
    session_mgr = _make_session_mgr(
        session=session,
        execute_result={"stdout": "hello world", "exit_status": 0, "working_directory": "/tmp"},
    )

    result = await _execute_command_logic(
        command="echo hello",
        node=None,
        session_id="s1",
        timeout=30,
        confirm_token=None,
        bypass_scope=None,
        pool=MagicMock(),
        guard=guard,
        token_store=_make_token_store(),
        session_mgr=session_mgr,
        db_session_ctx=_noop_db_session,
        node_repo_factory=_noop_node_repo_factory,
    )

    assert result == "hello world"
    session_mgr.execute.assert_awaited_once_with("s1", "echo hello", timeout=30)


@pytest.mark.asyncio
async def test_blocked_command_rejected():
    """When guard returns BLOCK, the command should be rejected immediately."""
    session = SSHSession(session_id="s1", node_id="node1")
    guard = _make_guard(SecurityLevel.BLOCK, message="rm is forbidden")
    session_mgr = _make_session_mgr(session=session)

    result = await _execute_command_logic(
        command="rm -rf /",
        node=None,
        session_id="s1",
        timeout=30,
        confirm_token=None,
        bypass_scope=None,
        pool=MagicMock(),
        guard=guard,
        token_store=_make_token_store(),
        session_mgr=session_mgr,
        db_session_ctx=_noop_db_session,
        node_repo_factory=_noop_node_repo_factory,
    )

    assert result.startswith("BLOCKED:")
    assert "rm is forbidden" in result
    session_mgr.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_confirm_returns_token_request():
    """When guard returns CONFIRM without a token, a confirmation message with token is returned."""
    session = SSHSession(session_id="s1", node_id="node1")
    guard = _make_guard(SecurityLevel.CONFIRM, message="Needs approval")
    token_store = _make_token_store()
    token_store.create.return_value = "tok_abc123"
    session_mgr = _make_session_mgr(session=session)

    result = await _execute_command_logic(
        command="shutdown -h now",
        node=None,
        session_id="s1",
        timeout=30,
        confirm_token=None,
        bypass_scope=None,
        pool=MagicMock(),
        guard=guard,
        token_store=token_store,
        session_mgr=session_mgr,
        db_session_ctx=_noop_db_session,
        node_repo_factory=_noop_node_repo_factory,
    )

    assert "confirm_token" in result
    assert "tok_abc123" in result
    token_store.create.assert_called_once_with("shutdown -h now", "node1")
    session_mgr.execute.assert_not_awaited()
