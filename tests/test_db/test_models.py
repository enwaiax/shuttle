"""Tests for SQLAlchemy ORM models."""

import pytest
from sqlalchemy import select

from shuttle.db.models import CommandLog, Node, SecurityRule, Session


@pytest.mark.asyncio
async def test_node_creation(db_session):
    """Test creating a node and persisting it."""
    node = Node(
        name="test-server",
        host="192.168.1.10",
        port=22,
        username="admin",
        auth_type="password",
        encrypted_credential="enc:abc123",
        status="active",
    )
    db_session.add(node)
    await db_session.commit()

    result = await db_session.execute(select(Node).where(Node.name == "test-server"))
    fetched = result.scalar_one()
    assert fetched.name == "test-server"
    assert fetched.host == "192.168.1.10"
    assert fetched.port == 22
    assert fetched.username == "admin"
    assert fetched.id is not None


@pytest.mark.asyncio
async def test_node_jump_host_fk(db_session):
    """Test jump host self-referential FK."""
    jump_host = Node(
        name="jump",
        host="10.0.0.1",
        port=22,
        username="juser",
        auth_type="key",
        encrypted_credential="enc:xyz",
        status="active",
    )
    db_session.add(jump_host)
    await db_session.commit()

    target = Node(
        name="target",
        host="192.168.50.1",
        port=22,
        username="tuser",
        auth_type="key",
        encrypted_credential="enc:xyz2",
        jump_host_id=jump_host.id,
        status="active",
    )
    db_session.add(target)
    await db_session.commit()

    result = await db_session.execute(select(Node).where(Node.name == "target"))
    fetched = result.scalar_one()
    assert fetched.jump_host_id == jump_host.id


@pytest.mark.asyncio
async def test_security_rule_creation(db_session):
    """Test creating a security rule."""
    node = Node(
        name="node-sr",
        host="10.1.1.1",
        port=22,
        username="u",
        auth_type="password",
        encrypted_credential="enc:pass",
        status="active",
    )
    db_session.add(node)
    await db_session.commit()

    rule = SecurityRule(
        pattern=r"rm\s+-rf",
        level="blocked",
        node_id=node.id,
        description="Block dangerous rm",
        priority=10,
        enabled=True,
    )
    db_session.add(rule)
    await db_session.commit()

    result = await db_session.execute(
        select(SecurityRule).where(SecurityRule.node_id == node.id)
    )
    fetched = result.scalar_one()
    assert fetched.pattern == r"rm\s+-rf"
    assert fetched.level == "blocked"
    assert fetched.priority == 10


@pytest.mark.asyncio
async def test_session_creation(db_session):
    """Test creating a session linked to a node."""
    node = Node(
        name="node-sess",
        host="10.2.2.2",
        port=22,
        username="u",
        auth_type="key",
        encrypted_credential="enc:key",
        status="active",
    )
    db_session.add(node)
    await db_session.commit()

    session = Session(
        node_id=node.id,
        working_directory="/home/u",
        status="active",
    )
    db_session.add(session)
    await db_session.commit()

    result = await db_session.execute(
        select(Session).where(Session.node_id == node.id)
    )
    fetched = result.scalar_one()
    assert fetched.working_directory == "/home/u"
    assert fetched.status == "active"
    assert fetched.node_id == node.id


@pytest.mark.asyncio
async def test_command_log_creation(db_session):
    """Test creating a command log entry."""
    node = Node(
        name="node-cmd",
        host="10.3.3.3",
        port=22,
        username="u",
        auth_type="password",
        encrypted_credential="enc:p",
        status="active",
    )
    db_session.add(node)
    await db_session.commit()

    session = Session(node_id=node.id, working_directory="/", status="active")
    db_session.add(session)
    await db_session.commit()

    log = CommandLog(
        session_id=session.id,
        node_id=node.id,
        command="ls -la",
        exit_code=0,
        stdout="total 12\n...",
        stderr="",
        security_level="safe",
        bypassed=False,
        duration_ms=42,
    )
    db_session.add(log)
    await db_session.commit()

    result = await db_session.execute(
        select(CommandLog).where(CommandLog.session_id == session.id)
    )
    fetched = result.scalar_one()
    assert fetched.command == "ls -la"
    assert fetched.exit_code == 0
    assert fetched.duration_ms == 42


@pytest.mark.asyncio
async def test_command_log_nullable_session(db_session):
    """Test that CommandLog.session_id is nullable (stateless execution)."""
    node = Node(
        name="node-stateless",
        host="10.4.4.4",
        port=22,
        username="u",
        auth_type="password",
        encrypted_credential="enc:p",
        status="active",
    )
    db_session.add(node)
    await db_session.commit()

    log = CommandLog(
        session_id=None,  # stateless — no session
        node_id=node.id,
        command="whoami",
        exit_code=0,
        stdout="root\n",
        stderr="",
        security_level="safe",
        bypassed=False,
        duration_ms=10,
    )
    db_session.add(log)
    await db_session.commit()

    result = await db_session.execute(
        select(CommandLog).where(CommandLog.node_id == node.id)
    )
    fetched = result.scalar_one()
    assert fetched.session_id is None
    assert fetched.command == "whoami"
