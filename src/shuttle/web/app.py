"""FastAPI application factory."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from shuttle.db.engine import init_db
from shuttle.web.deps import _engine, init_db_deps, verify_token


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    if _engine is not None:
        await init_db(_engine)
    yield


def create_app(
    db_url: str | None = None,
    api_token: str | None = None,
) -> FastAPI:
    """Build and return the FastAPI application."""
    init_db_deps(db_url, api_token=api_token)

    app = FastAPI(
        title="Shuttle",
        description="Shuttle Web Control Panel API",
        version="0.1.0",
        lifespan=lifespan,
        dependencies=[Depends(verify_token)],
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from shuttle.web.routes import logs, nodes, rules, sessions, stats

    app.include_router(stats.router, prefix="/api")
    app.include_router(nodes.router, prefix="/api")
    app.include_router(rules.router, prefix="/api")
    app.include_router(sessions.router, prefix="/api")
    app.include_router(logs.router, prefix="/api")

    static_dir = Path(__file__).parent / "static"
    if static_dir.is_dir() and (static_dir / "index.html").exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True))

    return app
