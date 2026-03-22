"""Tests for ConnectionPool, PoolConfig, and PooledConnection."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shuttle.core.connection_pool import ConnectionPool, PoolConfig, PooledConnection
from shuttle.core.proxy import NodeConnectInfo

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_info(node_id: str = "test-node") -> NodeConnectInfo:
    return NodeConnectInfo(
        node_id=node_id,
        hostname="localhost",
        username="testuser",
    )


def make_mock_conn(*, closing: bool = False) -> MagicMock:
    """Return a mock asyncssh connection."""
    conn = MagicMock()
    conn.is_closed.return_value = closing
    conn.close = MagicMock()
    return conn


def make_pooled(
    node_id: str = "test-node", *, closing: bool = False
) -> PooledConnection:
    return PooledConnection(conn=make_mock_conn(closing=closing), node_id=node_id)


# ---------------------------------------------------------------------------
# PoolConfig defaults
# ---------------------------------------------------------------------------


def test_pool_config_defaults():
    cfg = PoolConfig()
    assert cfg.max_per_node == 5
    assert cfg.max_total == 50
    assert cfg.idle_timeout == 300.0
    assert cfg.max_lifetime == 3600.0


def test_pool_config_custom():
    cfg = PoolConfig(
        max_per_node=2, max_total=10, idle_timeout=60.0, max_lifetime=600.0
    )
    assert cfg.max_per_node == 2
    assert cfg.max_total == 10
    assert cfg.idle_timeout == 60.0
    assert cfg.max_lifetime == 600.0


# ---------------------------------------------------------------------------
# PooledConnection expiry
# ---------------------------------------------------------------------------


def test_pooled_connection_not_expired_fresh():
    pc = make_pooled()
    assert not pc.is_expired(idle_timeout=300.0, max_lifetime=3600.0)


def test_pooled_connection_expired_idle(monkeypatch):
    pc = make_pooled()
    # Simulate time passing beyond idle_timeout
    monkeypatch.setattr(time, "monotonic", lambda: pc.last_used_at + 301)
    assert pc.is_expired(idle_timeout=300.0, max_lifetime=3600.0)


def test_pooled_connection_expired_lifetime(monkeypatch):
    pc = make_pooled()
    # Simulate time passing beyond max_lifetime
    monkeypatch.setattr(time, "monotonic", lambda: pc.created_at + 3601)
    assert pc.is_expired(idle_timeout=300.0, max_lifetime=3600.0)


def test_pooled_connection_touch_updates_last_used():
    pc = make_pooled()
    original = pc.last_used_at
    # Small sleep to ensure time advances
    time.sleep(0.01)
    pc.touch()
    assert pc.last_used_at >= original


# ---------------------------------------------------------------------------
# acquire / release / reuse
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_acquire_creates_new_connection():
    pool = ConnectionPool(PoolConfig(max_per_node=2))
    info = make_info()
    pool.register_node(info)

    mock_conn = make_mock_conn()

    with patch(
        "shuttle.core.connection_pool.connect_ssh",
        new_callable=AsyncMock,
        return_value=mock_conn,
    ):
        pc = await pool.acquire("test-node")

    assert pc.node_id == "test-node"
    assert pc.conn is mock_conn
    assert pool._active["test-node"] == 1


@pytest.mark.asyncio
async def test_release_puts_connection_in_idle():
    pool = ConnectionPool(PoolConfig(max_per_node=2))
    info = make_info()
    pool.register_node(info)

    mock_conn = make_mock_conn()

    with patch(
        "shuttle.core.connection_pool.connect_ssh",
        new_callable=AsyncMock,
        return_value=mock_conn,
    ):
        pc = await pool.acquire("test-node")

    await pool.release(pc)

    assert pool._active["test-node"] == 0
    assert len(pool._idle["test-node"]) == 1


@pytest.mark.asyncio
async def test_acquire_reuses_idle_connection():
    pool = ConnectionPool(PoolConfig(max_per_node=2))
    info = make_info()
    pool.register_node(info)

    mock_conn = make_mock_conn()

    with patch(
        "shuttle.core.connection_pool.connect_ssh",
        new_callable=AsyncMock,
        return_value=mock_conn,
    ) as mock_create:
        pc1 = await pool.acquire("test-node")
        await pool.release(pc1)

        # Second acquire should reuse the idle connection without creating a new one
        pc2 = await pool.acquire("test-node")

    assert mock_create.call_count == 1  # Only one real connection created
    assert pc2.conn is mock_conn


@pytest.mark.asyncio
async def test_acquire_raises_when_max_per_node_reached():
    pool = ConnectionPool(PoolConfig(max_per_node=1))
    info = make_info()
    pool.register_node(info)

    mock_conn = make_mock_conn()

    with patch(
        "shuttle.core.connection_pool.connect_ssh",
        new_callable=AsyncMock,
        return_value=mock_conn,
    ):
        _pc = await pool.acquire("test-node")

        with pytest.raises(RuntimeError, match="Per-node limit reached"):
            await pool.acquire("test-node")


@pytest.mark.asyncio
async def test_acquire_raises_for_unregistered_node():
    pool = ConnectionPool()
    with pytest.raises(KeyError, match="not registered"):
        await pool.acquire("ghost-node")


# ---------------------------------------------------------------------------
# max_total global limit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_global_limit_enforced():
    pool = ConnectionPool(PoolConfig(max_per_node=5, max_total=1))
    info_a = make_info("node-a")
    info_b = make_info("node-b")
    pool.register_node(info_a)
    pool.register_node(info_b)

    mock_conn = make_mock_conn()

    with patch(
        "shuttle.core.connection_pool.connect_ssh",
        new_callable=AsyncMock,
        return_value=mock_conn,
    ):
        await pool.acquire("node-a")

        with pytest.raises(RuntimeError, match="Global connection limit"):
            await pool.acquire("node-b")


# ---------------------------------------------------------------------------
# context manager
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_connection_context_manager():
    pool = ConnectionPool()
    info = make_info()
    pool.register_node(info)

    mock_conn = make_mock_conn()

    with patch(
        "shuttle.core.connection_pool.connect_ssh",
        new_callable=AsyncMock,
        return_value=mock_conn,
    ):
        async with pool.connection("test-node") as pc:
            assert pc.node_id == "test-node"

    # After context exit the connection should be in the idle pool
    assert pool._active["test-node"] == 0


@pytest.mark.asyncio
async def test_connection_context_manager_releases_on_error():
    pool = ConnectionPool()
    info = make_info()
    pool.register_node(info)

    mock_conn = make_mock_conn()

    with patch(
        "shuttle.core.connection_pool.connect_ssh",
        new_callable=AsyncMock,
        return_value=mock_conn,
    ):
        with pytest.raises(ValueError):
            async with pool.connection("test-node"):
                raise ValueError("boom")

    assert pool._active["test-node"] == 0


# ---------------------------------------------------------------------------
# close_all
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_close_all_closes_idle_connections():
    pool = ConnectionPool()
    info = make_info()
    pool.register_node(info)

    mock_conn = make_mock_conn()

    with patch(
        "shuttle.core.connection_pool.connect_ssh",
        new_callable=AsyncMock,
        return_value=mock_conn,
    ):
        pc = await pool.acquire("test-node")
        await pool.release(pc)

    assert len(pool._idle["test-node"]) == 1

    await pool.close_all()

    assert "test-node" not in pool._idle or len(pool._idle["test-node"]) == 0
    mock_conn.close.assert_called()


# ---------------------------------------------------------------------------
# evict_expired
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evict_expired_removes_old_connections(monkeypatch):
    pool = ConnectionPool(PoolConfig(idle_timeout=10.0, max_lifetime=3600.0))
    info = make_info()
    pool.register_node(info)

    mock_conn = make_mock_conn()

    with patch(
        "shuttle.core.connection_pool.connect_ssh",
        new_callable=AsyncMock,
        return_value=mock_conn,
    ):
        pc = await pool.acquire("test-node")
        await pool.release(pc)

    assert len(pool._idle["test-node"]) == 1

    # Fast-forward time so the connection is idle-expired
    monkeypatch.setattr(time, "monotonic", lambda: pc.last_used_at + 11)

    evicted = await pool.evict_expired()
    assert evicted == 1
    assert len(pool._idle["test-node"]) == 0


@pytest.mark.asyncio
async def test_evict_expired_keeps_fresh_connections():
    pool = ConnectionPool(PoolConfig(idle_timeout=300.0))
    info = make_info()
    pool.register_node(info)

    mock_conn = make_mock_conn()

    with patch(
        "shuttle.core.connection_pool.connect_ssh",
        new_callable=AsyncMock,
        return_value=mock_conn,
    ):
        pc = await pool.acquire("test-node")
        await pool.release(pc)

    evicted = await pool.evict_expired()
    assert evicted == 0
    assert len(pool._idle["test-node"]) == 1
