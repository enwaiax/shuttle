"""Approval concurrency tests."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from shuttle.db.models import Base
from shuttle.db.repository import ApprovalRepo, NodeRepo


@pytest.mark.asyncio
async def test_approval_consumption_is_atomic(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'race.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        node = await NodeRepo(session).create(
            name="race-node",
            host="127.0.0.1",
            username="runner",
            encrypted_credential="enc",
        )
        request = await ApprovalRepo(session).create(
            node_id=node.id,
            node_name=node.name,
            command="sudo true",
            command_hash="d" * 64,
            actor_id="alice",
            client_id="hermes",
            conversation_id="race",
            status="approved",
            approver="operator",
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )

    async def consume_once():
        async with factory() as session:
            return await ApprovalRepo(session).consume(request.id)

    results = await asyncio.gather(*[consume_once() for _ in range(20)])
    assert sum(result is not None for result in results) == 1
    await engine.dispose()
