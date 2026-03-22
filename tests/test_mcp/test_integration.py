"""Integration tests for the Shuttle MCP server.

These tests exercise the full server creation path with a real in-memory
SQLite database but no real SSH connections.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from shuttle.db.models import SecurityRule
from shuttle.mcp.server import create_mcp_server

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _patched_pool():
    """Return a mocked ConnectionPool that skips SSH connections and eviction."""
    mock_pool = MagicMock()
    mock_pool._registry = {}
    mock_pool.start_eviction_loop = AsyncMock()
    mock_pool.register_node = MagicMock()
    return mock_pool


def _patched_session_mgr():
    """Return a mocked SessionManager."""
    mock_session_mgr = MagicMock()
    mock_session_mgr.list_active.return_value = []
    return mock_session_mgr


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mcp_server_starts_and_lists_nodes(tmp_path):
    """Full integration: server starts, tools are registered, ssh_list_nodes works."""
    shuttle_dir = tmp_path / ".shuttle"
    shuttle_dir.mkdir()
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"

    with (
        patch("shuttle.mcp.server.ConnectionPool") as MockPool,
        patch("shuttle.mcp.server.SessionManager") as MockSessionMgr,
    ):
        MockPool.return_value = _patched_pool()
        MockSessionMgr.return_value = _patched_session_mgr()

        mcp = await create_mcp_server(shuttle_dir=shuttle_dir, db_url=db_url)

    # Verify it's a FastMCP instance
    from fastmcp import FastMCP

    assert isinstance(mcp, FastMCP)

    # Verify required tools are registered
    tools = await mcp.get_tools()
    tool_names = set(tools.keys())
    required_tools = {"ssh_execute", "ssh_list_nodes", "ssh_session_start"}
    assert required_tools.issubset(tool_names), (
        f"Missing tools: {required_tools - tool_names}"
    )

    # Call ssh_list_nodes — should return onboarding message since no nodes configured
    # Use the tool's underlying fn directly to avoid needing an active MCP context
    tool = await mcp.get_tool("ssh_list_nodes")
    output = await tool.fn()
    assert isinstance(output, str)
    assert "No nodes configured" in output


@pytest.mark.asyncio
async def test_default_security_rules_seeded(tmp_path):
    """Default security rules are seeded on first server startup."""
    shuttle_dir = tmp_path / ".shuttle"
    shuttle_dir.mkdir()
    db_path = tmp_path / "test.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"

    with (
        patch("shuttle.mcp.server.ConnectionPool") as MockPool,
        patch("shuttle.mcp.server.SessionManager") as MockSessionMgr,
    ):
        MockPool.return_value = _patched_pool()
        MockSessionMgr.return_value = _patched_session_mgr()

        await create_mcp_server(shuttle_dir=shuttle_dir, db_url=db_url)

    # Open a fresh DB connection to verify rules were seeded
    engine = create_async_engine(db_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            from sqlalchemy import select

            result = await session.execute(select(SecurityRule))
            rules = result.scalars().all()

        assert len(rules) >= 10, (
            f"Expected at least 10 default security rules, got {len(rules)}"
        )

        # Verify we have all three levels
        levels = {r.level for r in rules}
        assert "block" in levels, "Expected at least one 'block' rule"
        assert "confirm" in levels, "Expected at least one 'confirm' rule"
        assert "warn" in levels, "Expected at least one 'warn' rule"
    finally:
        await engine.dispose()
