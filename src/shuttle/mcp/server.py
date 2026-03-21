"""MCP server orchestration — wires up all Shuttle components into a FastMCP instance."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, Optional

from fastapi import FastAPI
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
from shuttle.db.repository import NodeRepo
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
    4. Create CommandGuard (rules queried per-call from DB)
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

    # ── 4. Security guard (rules queried per-call from DB) ──────────
    guard = CommandGuard()

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
        cred_mgr=cred_mgr,
    )

    # ── 12. Return ──────────────────────────────────────────────────
    return mcp


async def create_service_app(
    host: str = "127.0.0.1",
    port: int = 9876,
    api_token: str | None = None,
    shuttle_dir: Optional[Path] = None,
    db_url: Optional[str] = None,
) -> FastAPI:
    """Create a unified ASGI app with FastMCP mounted at /mcp and FastAPI at /.

    This is the entry point for ``shuttle serve`` — a single HTTP server that
    exposes both the MCP endpoint and the web control panel.
    """
    from fastapi import Depends
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles

    from shuttle.db.seeds import seed_default_rules
    from shuttle.web.deps import init_db_deps, verify_token

    # ── Config ───────────────────────────────────────────────────────
    config = ShuttleConfig()
    if shuttle_dir is not None:
        config.shuttle_dir = shuttle_dir
    if db_url is not None:
        config.db_url = db_url

    config.shuttle_dir.mkdir(parents=True, exist_ok=True)

    # ── PID file ─────────────────────────────────────────────────────
    pid_file = config.shuttle_dir / "shuttle.pid"
    pid_file.write_text(str(os.getpid()))

    # ── DB engine + init ─────────────────────────────────────────────
    resolved_db_url = config.db_url
    if ":///" in resolved_db_url and "~" in resolved_db_url:
        resolved_db_url = resolved_db_url.replace("~", str(Path.home()))

    engine = create_db_engine(resolved_db_url)
    session_factory = create_session_factory(engine)

    # ── Core objects ─────────────────────────────────────────────────
    guard = CommandGuard()

    pool_config = PoolConfig(
        max_per_node=config.pool_max_per_node,
        max_total=config.pool_max_total,
        idle_timeout=float(config.pool_idle_timeout),
        max_lifetime=float(config.pool_max_lifetime),
    )
    pool = ConnectionPool(config=pool_config)

    cred_mgr = CredentialManager(config.shuttle_dir)
    token_store = ConfirmTokenStore()

    @asynccontextmanager
    async def db_session_ctx() -> AsyncIterator[AsyncSession]:
        async with session_factory() as sess:
            yield sess

    session_mgr = SessionManager(pool=pool, db_session_factory=db_session_ctx)

    # ── FastMCP + tools ──────────────────────────────────────────────
    mcp = FastMCP(name="shuttle")
    register_tools(
        mcp=mcp,
        pool=pool,
        guard=guard,
        token_store=token_store,
        session_mgr=session_mgr,
        db_session_ctx=db_session_ctx,
        node_repo_factory=NodeRepo,
        cred_mgr=cred_mgr,
    )

    mcp_http = mcp.http_app(path="/")

    # ── Combined lifespan ────────────────────────────────────────────
    @asynccontextmanager
    async def combined_lifespan(app: FastAPI):
        # Startup: init DB, seed rules, register nodes, start pool
        await init_db(engine)
        async with session_factory() as db_sess:
            seeded = await seed_default_rules(db_sess)
            if seeded:
                logger.info("Seeded {n} default security rules", n=seeded)

        # Register nodes from DB
        async with session_factory() as db_sess:
            node_repo = NodeRepo(db_sess)
            nodes = await node_repo.list_all()

        for node in nodes:
            try:
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
                logger.warning("Failed to register node '{name}' — skipping", name=node.name)

        logger.info("Registered {n} nodes in pool", n=len(pool._registry))
        await pool.start_eviction_loop()

        # Run MCP lifespan within the combined lifespan
        async with mcp_http.lifespan(mcp_http):
            yield

        # Shutdown — close pool with timeout to avoid hanging on Ctrl+C
        import asyncio
        try:
            await asyncio.wait_for(pool.close_all(), timeout=3.0)
        except asyncio.TimeoutError:
            logger.warning("Connection pool close timed out — forcing shutdown")
        await engine.dispose()

    # ── Inject shared deps into web layer ────────────────────────────
    init_db_deps(api_token=api_token, engine=engine, session_factory=session_factory)

    # ── FastAPI app ──────────────────────────────────────────────────
    # Note: verify_token is applied per-router (not globally) so that
    # /mcp/* endpoints are not gated by the web panel token.
    app = FastAPI(
        title="Shuttle",
        version="0.2.0",
        lifespan=combined_lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routes — token auth applied per-router so /mcp is not gated
    from shuttle.web.routes import data, logs, nodes, rules, sessions, settings, stats

    api_deps = [Depends(verify_token)]
    app.include_router(stats.router, prefix="/api", dependencies=api_deps)
    app.include_router(nodes.router, prefix="/api", dependencies=api_deps)
    app.include_router(rules.router, prefix="/api", dependencies=api_deps)
    app.include_router(sessions.router, prefix="/api", dependencies=api_deps)
    app.include_router(logs.router, prefix="/api", dependencies=api_deps)
    app.include_router(settings.router, prefix="/api", dependencies=api_deps)
    app.include_router(data.router, prefix="/api", dependencies=api_deps)

    # Mount MCP — Starlette mount strips trailing path, so sub-app
    # with path="/" receives requests at /mcp/*. The MCP client posts to
    # /mcp/ (with trailing slash) which the sub-app handles at "/".
    # We also add a redirect from /mcp → /mcp/ for clients that omit the slash.
    from starlette.responses import RedirectResponse

    @app.api_route("/mcp", methods=["GET", "POST", "DELETE"], include_in_schema=False)
    async def mcp_redirect():
        return RedirectResponse(url="/mcp/", status_code=307)

    app.mount("/mcp", mcp_http)

    # SPA static files + catch-all fallback for client-side routing
    static_dir = Path(__file__).resolve().parent.parent / "web" / "static"
    if static_dir.is_dir() and (static_dir / "index.html").exists():
        # Serve actual static assets (JS, CSS, etc.)
        app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")))

        # Catch-all: return index.html for any non-API, non-MCP route
        from starlette.responses import FileResponse

        @app.get("/{path:path}", include_in_schema=False)
        async def spa_fallback(path: str):
            # Don't intercept API or MCP routes
            if path.startswith("api/") or path.startswith("mcp"):
                from fastapi import HTTPException
                raise HTTPException(404)
            return FileResponse(str(static_dir / "index.html"))

    return app
