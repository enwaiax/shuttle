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

        # Create indexes if they don't exist (idempotent for existing DBs)
        for idx_sql in [
            "CREATE INDEX IF NOT EXISTS ix_command_logs_node_executed ON command_logs (node_id, executed_at)",
            "CREATE INDEX IF NOT EXISTS ix_command_logs_session ON command_logs (session_id)",
            "CREATE INDEX IF NOT EXISTS ix_security_rules_node ON security_rules (node_id)",
            "CREATE INDEX IF NOT EXISTS ix_sessions_node_status ON sessions (node_id, status)",
        ]:
            try:
                await conn.execute(text(idx_sql))
            except Exception:
                pass  # Index might already exist or DB doesn't support IF NOT EXISTS

        # Migration: add source_rule_id if missing (v1 → v2)
        if "sqlite" in str(engine.url):
            result = await conn.execute(text("PRAGMA table_info(security_rules)"))
            columns = [row[1] for row in result]
            if "source_rule_id" not in columns:
                await conn.execute(
                    text(
                        "ALTER TABLE security_rules ADD COLUMN source_rule_id VARCHAR(36)"
                    )
                )

            # Migration: add latency_ms + last_seen_at to nodes
            result2 = await conn.execute(text("PRAGMA table_info(nodes)"))
            node_columns = [row[1] for row in result2]
            if "latency_ms" not in node_columns:
                await conn.execute(
                    text("ALTER TABLE nodes ADD COLUMN latency_ms INTEGER")
                )
            if "last_seen_at" not in node_columns:
                await conn.execute(
                    text("ALTER TABLE nodes ADD COLUMN last_seen_at DATETIME")
                )
        else:
            result = await conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'security_rules' AND column_name = 'source_rule_id'"
                )
            )
            if not result.fetchone():
                await conn.execute(
                    text(
                        "ALTER TABLE security_rules ADD COLUMN source_rule_id VARCHAR(36)"
                    )
                )

            # Migration: add latency_ms + last_seen_at to nodes
            result2 = await conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'nodes' AND column_name = 'latency_ms'"
                )
            )
            if not result2.fetchone():
                await conn.execute(
                    text("ALTER TABLE nodes ADD COLUMN latency_ms INTEGER")
                )
                await conn.execute(
                    text("ALTER TABLE nodes ADD COLUMN last_seen_at TIMESTAMP WITH TIME ZONE")
                )
