"""Tests for create_service_app (unified MCP + web ASGI app)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient


def _mock_pool():
    p = MagicMock()
    p._registry = {}
    p.start_eviction_loop = AsyncMock()
    p.register_node = MagicMock()
    p.close_all = AsyncMock()
    return p


def _mock_session_mgr():
    m = MagicMock()
    m.list_active.return_value = []
    return m


@pytest.mark.asyncio
async def test_create_service_app_exposes_stats_with_bearer(tmp_path):
    shuttle_dir = tmp_path / ".shuttle"
    shuttle_dir.mkdir()
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'svc.db'}"
    token = "test-bearer-token"

    with (
        patch("shuttle.mcp.server.ConnectionPool", return_value=_mock_pool()),
        patch("shuttle.mcp.server.SessionManager", return_value=_mock_session_mgr()),
    ):
        from shuttle.mcp.server import create_service_app

        app = await create_service_app(
            shuttle_dir=shuttle_dir,
            db_url=db_url,
            api_token=token,
            port=19999,
        )

    transport = ASGITransport(app=app)
    async with LifespanManager(app):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get(
                "/api/stats", headers={"Authorization": f"Bearer {token}"}
            )
            assert r.status_code == 200
            data = r.json()
            assert "node_count" in data

            redir = await client.get("/mcp", follow_redirects=False)
            assert redir.status_code == 307
            assert redir.headers.get("location", "").endswith("/mcp/")


@pytest.mark.asyncio
async def test_create_service_app_rejects_bad_bearer(tmp_path):
    shuttle_dir = tmp_path / ".shuttle"
    shuttle_dir.mkdir()
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'svc2.db'}"

    with (
        patch("shuttle.mcp.server.ConnectionPool", return_value=_mock_pool()),
        patch("shuttle.mcp.server.SessionManager", return_value=_mock_session_mgr()),
    ):
        from shuttle.mcp.server import create_service_app

        app = await create_service_app(
            shuttle_dir=shuttle_dir,
            db_url=db_url,
            api_token="good",
        )

    transport = ASGITransport(app=app)
    async with LifespanManager(app):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get(
                "/api/stats", headers={"Authorization": "Bearer wrong"}
            )
            assert r.status_code == 401
