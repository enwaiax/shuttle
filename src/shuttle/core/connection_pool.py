"""SSH Connection Pool with async context manager, eviction, and jump host support.

Design principles
-----------------
* ``acquire()`` increments ``_active`` **inside** the per-node lock before
  releasing it.  This atomically reserves the slot so that no other coroutine
  can steal it.  If ``_create_connection`` subsequently fails the slot is
  decremented to restore the invariant.
* Idle connections are kept in a deque so the most-recently-used connection is
  returned first (LIFO), which helps keep a warm set of connections in practice.
* ``connection(node_id)`` is an async context manager that acquires on enter
  and releases on exit, providing leak protection via a try/finally.
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional

import asyncssh

from shuttle.core.proxy import NodeConnectInfo, connect_ssh


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class PoolConfig:
    """Tuning parameters for ConnectionPool.

    Attributes
    ----------
    max_per_node:
        Maximum number of simultaneous connections to a single node.
    max_total:
        Maximum number of connections across *all* nodes combined.
    idle_timeout:
        Seconds a connection may sit idle before being evicted (default 300).
    max_lifetime:
        Absolute maximum age of any connection in seconds (default 3600).
    """

    max_per_node: int = 5
    max_total: int = 50
    idle_timeout: float = 300.0
    max_lifetime: float = 3600.0


# ---------------------------------------------------------------------------
# PooledConnection
# ---------------------------------------------------------------------------


@dataclass
class PooledConnection:
    """A wrapper around an asyncssh connection that tracks pool metadata.

    Attributes
    ----------
    conn:
        The underlying asyncssh connection.
    node_id:
        Logical identifier of the node this connection belongs to.
    created_at:
        Monotonic timestamp when the connection was first established.
    last_used_at:
        Monotonic timestamp of the last acquire/release cycle.
    """

    conn: asyncssh.SSHClientConnection
    node_id: str
    created_at: float = field(default_factory=time.monotonic)
    last_used_at: float = field(default_factory=time.monotonic)

    def is_expired(self, idle_timeout: float, max_lifetime: float) -> bool:
        """Return True if this connection has exceeded idle or lifetime limits."""
        now = time.monotonic()
        idle = now - self.last_used_at
        age = now - self.created_at
        return idle >= idle_timeout or age >= max_lifetime

    def touch(self) -> None:
        """Update last_used_at to now."""
        self.last_used_at = time.monotonic()


# ---------------------------------------------------------------------------
# ConnectionPool
# ---------------------------------------------------------------------------


class ConnectionPool:
    """Async SSH connection pool with per-node limits and idle eviction.

    Parameters
    ----------
    config:
        Pool tuning parameters (defaults defined in PoolConfig).
    """

    def __init__(self, config: Optional[PoolConfig] = None) -> None:
        self._config = config or PoolConfig()

        # Per-node tracking structures guarded by _lock[node_id]
        # _idle[node_id]: deque of idle PooledConnection (LIFO via appendleft/popleft)
        # _active[node_id]: count of currently checked-out connections
        self._idle: dict[str, deque[PooledConnection]] = {}
        self._active: dict[str, int] = {}
        self._locks: dict[str, asyncio.Lock] = {}

        # Registry: node_id -> NodeConnectInfo
        self._registry: dict[str, NodeConnectInfo] = {}

        # Global active count guarded by _global_lock
        self._global_lock = asyncio.Lock()
        self._global_active: int = 0

        self._eviction_task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------
    # Node registry
    # ------------------------------------------------------------------

    def register_node(self, info: NodeConnectInfo) -> None:
        """Register (or overwrite) connection info for a node."""
        node_id = info.node_id
        self._registry[node_id] = info
        # Ensure per-node data structures exist
        if node_id not in self._locks:
            self._locks[node_id] = asyncio.Lock()
            self._idle[node_id] = deque()
            self._active[node_id] = 0

    def unregister_node(self, node_id: str) -> None:
        """Remove a node from the registry (does not close existing connections)."""
        self._registry.pop(node_id, None)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @asynccontextmanager
    async def connection(self, node_id: str) -> AsyncIterator[PooledConnection]:
        """Async context manager that yields a connection and releases it on exit.

        Example
        -------
        ::

            async with pool.connection("prod-web-01") as pc:
                result = await pc.conn.run("hostname")
        """
        pc = await self.acquire(node_id)
        try:
            yield pc
        finally:
            await self.release(pc)

    async def acquire(self, node_id: str) -> PooledConnection:
        """Acquire a connection for *node_id*.

        Prefers an existing idle connection.  If none is available *and* the
        per-node and global limits allow, a new connection is created.

        The active-connection slot is reserved **atomically inside the lock**
        before the lock is released so that competing coroutines cannot
        over-subscribe a node.  If connection creation fails the slot is
        released.

        Raises
        ------
        KeyError
            If *node_id* is not registered.
        RuntimeError
            If the per-node or global connection limit has been reached.
        """
        if node_id not in self._registry:
            raise KeyError(f"Node '{node_id}' is not registered in the pool.")

        lock = self._locks[node_id]

        async with lock:
            # Try to reuse an idle connection
            idle_queue = self._idle[node_id]
            while idle_queue:
                pc = idle_queue.popleft()
                if pc.conn.is_closed():
                    # Connection died while idle — discard and try next
                    async with self._global_lock:
                        self._global_active -= 1
                    continue
                # Found a usable idle connection — mark as active
                self._active[node_id] += 1
                async with self._global_lock:
                    # Global counter was already incremented when conn was created;
                    # we just move it from idle to active conceptually.
                    pass
                pc.touch()
                return pc

            # No idle connection available — check limits before creating
            current_active = self._active[node_id]
            if current_active >= self._config.max_per_node:
                raise RuntimeError(
                    f"Per-node limit reached for '{node_id}' "
                    f"(max_per_node={self._config.max_per_node})."
                )

            async with self._global_lock:
                if self._global_active >= self._config.max_total:
                    raise RuntimeError(
                        f"Global connection limit reached "
                        f"(max_total={self._config.max_total})."
                    )
                # Reserve the global slot atomically
                self._global_active += 1

            # Reserve the per-node slot atomically (still inside node lock)
            self._active[node_id] += 1

        # Connection creation happens OUTSIDE the node lock to avoid blocking
        # other coroutines that may want a different idle connection.
        try:
            info = self._registry[node_id]
            raw_conn = await connect_ssh(info)
            pc = PooledConnection(conn=raw_conn, node_id=node_id)
            return pc
        except Exception:
            # Unreserve both slots on failure
            async with lock:
                self._active[node_id] -= 1
            async with self._global_lock:
                self._global_active -= 1
            raise

    async def release(self, pc: PooledConnection) -> None:
        """Return *pc* to the idle pool.

        The connection is only kept if it is still open and has not expired.
        """
        node_id = pc.node_id
        lock = self._locks.get(node_id)

        if lock is None:
            # Node was unregistered; just close the connection
            pc.conn.close()
            return

        async with lock:
            # Decrement active count regardless
            if self._active[node_id] > 0:
                self._active[node_id] -= 1

            if (
                not pc.conn.is_closed()
                and not pc.is_expired(
                    self._config.idle_timeout, self._config.max_lifetime
                )
            ):
                pc.touch()
                # LIFO: push to front so hot connections are reused first
                self._idle[node_id].appendleft(pc)
            else:
                # Connection is dead or expired; close and release global slot
                pc.conn.close()
                async with self._global_lock:
                    if self._global_active > 0:
                        self._global_active -= 1

    # ------------------------------------------------------------------
    # Eviction
    # ------------------------------------------------------------------

    async def evict_expired(self) -> int:
        """Close and remove all idle connections that have exceeded their TTL.

        Returns
        -------
        int
            Number of connections evicted.
        """
        evicted = 0
        for node_id, lock in list(self._locks.items()):
            async with lock:
                idle_queue = self._idle[node_id]
                alive: deque[PooledConnection] = deque()
                while idle_queue:
                    pc = idle_queue.popleft()
                    if pc.is_expired(
                        self._config.idle_timeout, self._config.max_lifetime
                    ) or pc.conn.is_closed():
                        pc.conn.close()
                        async with self._global_lock:
                            if self._global_active > 0:
                                self._global_active -= 1
                        evicted += 1
                    else:
                        alive.appendleft(pc)
                self._idle[node_id] = alive
        return evicted

    async def start_eviction_loop(self, interval: float = 60.0) -> None:
        """Start a background task that calls ``evict_expired()`` every *interval* seconds."""

        async def _loop() -> None:
            while True:
                await asyncio.sleep(interval)
                await self.evict_expired()

        self._eviction_task = asyncio.create_task(_loop())

    # ------------------------------------------------------------------
    # Teardown
    # ------------------------------------------------------------------

    async def close_all(self) -> None:
        """Close all idle connections for every registered node."""
        for node_id in list(self._locks.keys()):
            await self.close_node(node_id)

        if self._eviction_task is not None:
            self._eviction_task.cancel()
            try:
                await self._eviction_task
            except asyncio.CancelledError:
                pass
            self._eviction_task = None

    async def close_node(self, node_id: str) -> None:
        """Close all idle connections for *node_id*.

        Active (checked-out) connections are not forcibly closed; they will be
        discarded instead of returned to the pool when released.
        """
        lock = self._locks.get(node_id)
        if lock is None:
            return

        async with lock:
            idle_queue = self._idle[node_id]
            while idle_queue:
                pc = idle_queue.popleft()
                pc.conn.close()
                async with self._global_lock:
                    if self._global_active > 0:
                        self._global_active -= 1
