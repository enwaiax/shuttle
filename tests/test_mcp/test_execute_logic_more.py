"""Additional tests for _execute_command_logic and _truncate (MCP core)."""

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


def test_truncate_short_unchanged() -> None:
    assert _truncate("hello", 100) == "hello"


def test_truncate_appends_marker_when_over_limit() -> None:
    # Multi-byte UTF-8 (not confusable with ASCII — avoids RUF001)
    raw = "\u4e00" * 500
    out = _truncate(raw, 10)
    assert "truncated" in out
    assert len(out.encode("utf-8")) <= MAX_OUTPUT_BYTES


@pytest.mark.asyncio
async def test_execute_no_node_multi_nodes_error() -> None:
    guard = MagicMock(spec=CommandGuard)
    guard.evaluate = AsyncMock(return_value=SecurityDecision(level=SecurityLevel.ALLOW))

    repo = MagicMock()
    n1, n2 = MagicMock(), MagicMock()
    repo.list_all = AsyncMock(return_value=[n1, n2])

    @asynccontextmanager
    async def ctx():
        yield MagicMock()

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
        db_session_ctx=ctx,
        node_repo_factory=lambda _s: repo,
    )
    assert "cannot auto-select" in out


def _sm_with_session(session: SSHSession) -> MagicMock:
    mgr = MagicMock(spec=SessionManager)
    mgr.get.return_value = session
    mgr.list_active.return_value = [session]
    mgr.create = AsyncMock(return_value=session)
    mgr.execute = AsyncMock(
        return_value={"stdout": "x", "exit_status": 0, "working_directory": "/"}
    )
    return mgr


@pytest.mark.asyncio
async def test_execute_confirm_invalid_token() -> None:
    session = SSHSession(session_id="s1", node_id="n1")
    guard = MagicMock(spec=CommandGuard)
    guard.evaluate = AsyncMock(
        return_value=SecurityDecision(
            level=SecurityLevel.CONFIRM, matched_rule="r1", message="check"
        )
    )
    ts = MagicMock(spec=ConfirmTokenStore)
    ts.validate.return_value = False

    @asynccontextmanager
    async def ctx():
        yield MagicMock()

    nr = MagicMock()
    nr.get_by_name = AsyncMock(return_value=MagicMock(id="nid"))

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
        db_session_ctx=ctx,
        node_repo_factory=lambda _s: nr,
    )
    assert "invalid" in out.lower()


@pytest.mark.asyncio
async def test_execute_warn_still_runs_session_execute() -> None:
    session = SSHSession(session_id="s1", node_id="n1")
    guard = MagicMock(spec=CommandGuard)
    guard.evaluate = AsyncMock(
        return_value=SecurityDecision(
            level=SecurityLevel.WARN, matched_rule="w1", message="careful"
        )
    )

    @asynccontextmanager
    async def ctx():
        yield MagicMock()

    nr = MagicMock()
    nr.get_by_name = AsyncMock(return_value=MagicMock(id="nid"))
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
            db_session_ctx=ctx,
            node_repo_factory=lambda _s: nr,
        )
    log_warn.assert_called()
    assert out == "x"


@pytest.mark.asyncio
async def test_execute_auto_session_creation_on_pool_node() -> None:
    """When no session exists, auto-create one and execute via session_mgr."""
    new_session = SSHSession(session_id="auto-new", node_id="n1")
    guard = MagicMock(spec=CommandGuard)
    guard.evaluate = AsyncMock(return_value=SecurityDecision(level=SecurityLevel.ALLOW))

    mgr = MagicMock(spec=SessionManager)
    mgr.list_active.return_value = []
    mgr.create = AsyncMock(return_value=new_session)
    mgr.execute = AsyncMock(
        return_value={"stdout": "hello", "exit_status": 0, "working_directory": "/"}
    )

    @asynccontextmanager
    async def ctx():
        yield MagicMock()

    nr = MagicMock()
    nr.get_by_name = AsyncMock(return_value=MagicMock(id="nid"))

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
        db_session_ctx=ctx,
        node_repo_factory=lambda _s: nr,
    )
    assert out == "hello"
    mgr.create.assert_awaited_once_with("n1")
    mgr.execute.assert_awaited_once()
