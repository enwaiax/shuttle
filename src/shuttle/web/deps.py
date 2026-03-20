"""FastAPI dependency injection."""

from collections.abc import AsyncIterator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from shuttle.db.engine import create_db_engine, create_session_factory

_engine = None
_session_factory = None
_api_token: str | None = None

_bearer_scheme = HTTPBearer(auto_error=False)


def init_db_deps(
    db_url: str | None = None,
    api_token: str | None = None,
    engine=None,
    session_factory=None,
) -> None:
    """Initialize the module-level engine, session factory, and API token."""
    global _engine, _session_factory, _api_token
    _api_token = api_token
    if engine and session_factory:
        _engine = engine
        _session_factory = session_factory
    else:
        _engine = create_db_engine(db_url)
        _session_factory = create_session_factory(_engine)


async def verify_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> None:
    """Verify Bearer token on all /api/* routes. Skipped when no token is configured."""
    if _api_token is None:
        return
    if credentials is None or credentials.credentials != _api_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or missing token")


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Yield a DB session for each request; auto-commit on success."""
    if _session_factory is None:
        raise RuntimeError("DB not initialized — call init_db_deps() first")
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
