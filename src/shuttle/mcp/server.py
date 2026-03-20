"""MCP server orchestration — wires up all Shuttle components into a FastMCP instance."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, Optional

from fastmcp import FastMCP
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from shuttle.core.config import ShuttleConfig
from shuttle.core.connection_pool import ConnectionPool, PoolConfig
from shuttle.core.credentials import CredentialManager
from shuttle.core.proxy import NodeConnectInfo
from shuttle.core.security import CommandGuard, ConfirmTokenStore
from shuttle.core.session import SessionManager
from shuttle.db.engine import create_db_engine, create_session_factory, init_db
from shuttle.db.repository import LogRepo, NodeRepo, RuleRepo
from shuttle.mcp.tools import register_tools


async def create_mcp_server(
    shuttle_dir: Optional[Path] = None,
    db_url: Optional[str] = None,
) -> FastMCP:
    """Create and return a fully-wired FastMCP server instance.

    Steps:
    1. Create ShuttleConfig, ensure shuttle_dir exists
    2. Write PID file
    3. Create DB engine, init DB tables
    4. Load security rules from DB into CommandGuard
    5. Create ConnectionPool with config from ShuttleConfig
    6. Register node connection infos from DB (decrypt credentials, warn on failure)
    7. Start eviction loop
    8. Create ConfirmTokenStore and SessionManager
    9. Create FastMCP(name="shuttle")
    10. Create db_session_ctx async context manager
    11. Call register_tools with all dependencies
    12. Return FastMCP instance

    Parameters
    ----------
    shuttle_dir : Path | None
        Override the shuttle directory (defaults to ShuttleConfig's value).
    db_url : str | None
        Override the database URL (defaults to ShuttleConfig's value).

    Returns
    -------
    FastMCP
        The configured MCP server ready to run.
    """
    # ── 1. Config ───────────────────────────────────────────────────
    config = ShuttleConfig()
    if shuttle_dir is not None:
        config.shuttle_dir = shuttle_dir
    if db_url is not None:
        config.db_url = db_url

    config.shuttle_dir.mkdir(parents=True, exist_ok=True)

    # ── 2. PID file ─────────────────────────────────────────────────
    pid_file = config.shuttle_dir / "shuttle.pid"
    pid_file.write_text(str(os.getpid()))

    # ── 3. DB engine + init ─────────────────────────────────────────
    resolved_db_url = config.db_url
    # Expand ~ in sqlite paths
    if ":///" in resolved_db_url and "~" in resolved_db_url:
        resolved_db_url = resolved_db_url.replace("~", str(Path.home()))

    engine = create_db_engine(resolved_db_url)
    await init_db(engine)
    session_factory = create_session_factory(engine)

    # ── 3a. Seed default security rules ─────────────────────────────
    from shuttle.db.seeds import seed_default_rules
    async with session_factory() as db_session:
        seeded = await seed_default_rules(db_session)
    if seeded:
        logger.info("Seeded {n} default security rules", n=seeded)

    # ── 4. Load security rules ──────────────────────────────────────
    guard = CommandGuard()
    async with session_factory() as db_sess:
        rule_repo = RuleRepo(db_sess)
        db_rules = await rule_repo.list_all()
        guard.load_rules([
            {
                "name": r.id,
                "pattern": r.pattern,
                "level": r.level,
                "priority": r.priority,
                "message": r.description or "",
                "enabled": r.enabled,
            }
            for r in db_rules
        ])
    logger.info("Loaded {n} security rules", n=len(db_rules))

    # ── 5. Connection pool ──────────────────────────────────────────
    pool_config = PoolConfig(
        max_per_node=config.pool_max_per_node,
        max_total=config.pool_max_total,
        idle_timeout=float(config.pool_idle_timeout),
        max_lifetime=float(config.pool_max_lifetime),
    )
    pool = ConnectionPool(config=pool_config)

    # ── 6. Register nodes ───────────────────────────────────────────
    cred_mgr = CredentialManager(config.shuttle_dir)
    async with session_factory() as db_sess:
        node_repo = NodeRepo(db_sess)
        nodes = await node_repo.list_all()

    for node in nodes:
        try:
            # Decrypt the credential
            password = None
            private_key = None
            if node.encrypted_credential:
                decrypted = cred_mgr.decrypt(node.encrypted_credential)
                if node.auth_type == "key":
                    private_key = decrypted
                else:
                    password = decrypted

            info = NodeConnectInfo(
                node_id=node.name,
                hostname=node.host,
                port=node.port,
                username=node.username,
                password=password,
                private_key=private_key,
            )
            pool.register_node(info)
        except Exception:
            logger.warning(
                "Failed to register node '{name}' — skipping",
                name=node.name,
            )

    logger.info("Registered {n} nodes in pool", n=len(pool._registry))

    # ── 7. Eviction loop ────────────────────────────────────────────
    await pool.start_eviction_loop()

    # ── 8. Token store + session manager ────────────────────────────
    token_store = ConfirmTokenStore()

    @asynccontextmanager
    async def db_session_ctx() -> AsyncIterator[AsyncSession]:
        async with session_factory() as sess:
            yield sess

    session_mgr = SessionManager(pool=pool, db_session_factory=db_session_ctx)

    # ── 9. FastMCP ──────────────────────────────────────────────────
    mcp = FastMCP(name="shuttle")

    # ── 10-11. Register tools ───────────────────────────────────────
    register_tools(
        mcp=mcp,
        pool=pool,
        guard=guard,
        token_store=token_store,
        session_mgr=session_mgr,
        db_session_ctx=db_session_ctx,
        node_repo_factory=NodeRepo,
    )

    # ── 12. Return ──────────────────────────────────────────────────
    return mcp
