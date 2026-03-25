"""Tests for shuttle.mcp.server — create_mcp_server integration test."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shuttle.mcp.server import create_mcp_server

EXPECTED_TOOLS = {
    "ssh_run",
    "ssh_list_nodes",
    "ssh_upload",
    "ssh_download",
    "ssh_add_node",
}


@pytest.mark.asyncio
async def test_create_mcp_server_registers_expected_tools(tmp_path):
    """create_mcp_server returns a FastMCP with all 5 Shuttle tools registered."""
    shuttle_dir = tmp_path / ".shuttle"
    shuttle_dir.mkdir()
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"

    # Mock ConnectionPool to avoid SSH connections and eviction loop
    with (
        patch("shuttle.mcp.server.ConnectionPool") as MockPool,
        patch("shuttle.mcp.server.SessionManager") as MockSessionMgr,
    ):
        mock_pool = MagicMock()
        mock_pool._registry = {}
        mock_pool.start_eviction_loop = AsyncMock()
        mock_pool.register_node = MagicMock()
        MockPool.return_value = mock_pool

        mock_session_mgr = MagicMock()
        mock_session_mgr.list_active.return_value = []
        MockSessionMgr.return_value = mock_session_mgr

        mcp = await create_mcp_server(shuttle_dir=shuttle_dir, db_url=db_url)

    # Verify it's a FastMCP
    from fastmcp import FastMCP

    assert isinstance(mcp, FastMCP)

    # Verify all expected tools are registered
    tools = await mcp.get_tools()
    tool_names = set(tools.keys())
    assert EXPECTED_TOOLS.issubset(tool_names), (
        f"Missing tools: {EXPECTED_TOOLS - tool_names}"
    )
