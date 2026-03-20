"""Database engine creation and initialization for Shuttle."""

from pathlib import Path

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from shuttle.db.models import Base


def create_db_engine(url: str | None = None) -> AsyncEngine:
    """Create an async SQLAlchemy engine.

    Defaults to SQLite at ~/.shuttle/shuttle.db with WAL mode and busy_timeout
    pragmas for safe concurrent access.

    Args:
        url: Optional SQLAlchemy async database URL. Defaults to SQLite.

    Returns:
        Configured AsyncEngine instance.
    """
    if url is None:
        shuttle_dir = Path.home() / ".shuttle"
        shuttle_dir.mkdir(parents=True, exist_ok=True)
        db_path = shuttle_dir / "shuttle.db"
        url = f"sqlite+aiosqlite:///{db_path}"

    engine = create_async_engine(url, echo=False)

    # Apply SQLite-specific pragmas for WAL mode + busy timeout
    if url.startswith("sqlite"):

        @event.listens_for(engine.sync_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

    return engine


def create_session_factory(engine: AsyncEngine) -> sessionmaker:
    """Create an async session factory bound to the given engine.

    Args:
        engine: Async SQLAlchemy engine.

    Returns:
        Async sessionmaker that produces AsyncSession instances.
    """
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db(engine: AsyncEngine) -> None:
    """Create all database tables defined in the ORM models.

    Args:
        engine: Async SQLAlchemy engine to use for table creation.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
