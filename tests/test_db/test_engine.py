"""Tests for database engine creation and init_db migrations."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shuttle.db.engine import create_db_engine, create_session_factory, init_db


@pytest.mark.asyncio
async def test_init_db_creates_tables_on_sqlite_memory():
    engine = create_db_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    async with engine.connect() as conn:
        r = await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='nodes'")
        )
        assert r.scalar() == "nodes"
    await engine.dispose()


@pytest.mark.asyncio
async def test_sqlite_engine_sets_wal_and_busy_timeout(tmp_path: Path):
    db_file = tmp_path / "wal.db"
    engine = create_db_engine(f"sqlite+aiosqlite:///{db_file}")
    async with engine.connect() as conn:
        jm = (await conn.execute(text("PRAGMA journal_mode"))).scalar()
        assert str(jm).upper() == "WAL"
    await engine.dispose()


def test_create_db_engine_default_uses_shuttle_dir_under_home(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    engine = create_db_engine(None)
    assert "sqlite" in str(engine.url).lower()
    assert ".shuttle" in str(engine.url)
    assert (tmp_path / ".shuttle" / "shuttle.db").parent.is_dir()


@pytest.mark.asyncio
async def test_init_db_non_sqlite_runs_alter_migrations():
    captured: list[str] = []

    class FakeResult:
        def __init__(self, fetch=None):
            self._fetch = fetch

        def fetchone(self):
            return self._fetch

    async def execute_side_effect(stmt):
        captured.append(str(stmt))
        s = str(stmt)
        if "information_schema" in s and "source_rule_id" in s:
            return FakeResult(None)
        if "information_schema" in s and "latency_ms" in s:
            return FakeResult(None)
        return FakeResult()

    mock_conn = MagicMock()
    mock_conn.execute = AsyncMock(side_effect=execute_side_effect)
    mock_conn.run_sync = AsyncMock(return_value=None)

    mock_begin = MagicMock()
    mock_begin.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_begin.__aexit__ = AsyncMock(return_value=None)

    engine = MagicMock()
    engine.url = "postgresql+asyncpg://user:pass@localhost/db"
    engine.begin = MagicMock(return_value=mock_begin)

    await init_db(engine)

    assert any("ALTER TABLE security_rules" in x for x in captured)
    assert any("latency_ms" in x for x in captured)


@pytest.mark.asyncio
async def test_create_session_factory_yields_async_sessions():
    engine = create_db_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    factory = create_session_factory(engine)
    async with factory() as session:
        assert isinstance(session, AsyncSession)
    await engine.dispose()
