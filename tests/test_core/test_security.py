"""Tests for CommandGuard and ConfirmTokenStore."""

import time

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from shuttle.core.security import (
    CommandGuard,
    ConfirmTokenStore,
    SecurityLevel,
)
from shuttle.db.models import Base, SecurityRule

# ---------------------------------------------------------------------------
# SecurityLevel enum
# ---------------------------------------------------------------------------


def test_security_level_values():
    """SecurityLevel must expose the four expected string values."""
    assert SecurityLevel.BLOCK == "block"
    assert SecurityLevel.CONFIRM == "confirm"
    assert SecurityLevel.WARN == "warn"
    assert SecurityLevel.ALLOW == "allow"


# ---------------------------------------------------------------------------
# DB fixtures for CommandGuard tests
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def guard_db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def guard_db_session(guard_db_engine):
    async_session = sessionmaker(
        guard_db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session


async def _seed_sample_rules(session: AsyncSession) -> None:
    """Seed standard sample rules for most tests."""
    rules = [
        SecurityRule(
            pattern=r"rm\s+-rf\s+/",
            level="block",
            priority=10,
            description="Block rm -rf /",
            enabled=True,
        ),
        SecurityRule(
            pattern=r"\bsudo\b",
            level="confirm",
            priority=20,
            description="Confirm sudo",
            enabled=True,
        ),
        SecurityRule(
            pattern=r"\bcurl\b",
            level="warn",
            priority=30,
            description="Warn on curl",
            enabled=True,
        ),
        SecurityRule(
            pattern=r"^ls\b",
            level="allow",
            priority=40,
            description="Allow ls",
            enabled=True,
        ),
    ]
    session.add_all(rules)
    await session.commit()


# ---------------------------------------------------------------------------
# CommandGuard tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evaluate_block(guard_db_session):
    """A command matching a BLOCK rule must be blocked."""
    await _seed_sample_rules(guard_db_session)
    guard = CommandGuard()
    decision = await guard.evaluate("rm -rf /home", "node1", guard_db_session)
    assert decision.level == SecurityLevel.BLOCK
    assert decision.matched_rule is not None


@pytest.mark.asyncio
async def test_evaluate_confirm(guard_db_session):
    """A command matching a CONFIRM rule must require confirmation."""
    await _seed_sample_rules(guard_db_session)
    guard = CommandGuard()
    decision = await guard.evaluate("sudo apt-get update", "node1", guard_db_session)
    assert decision.level == SecurityLevel.CONFIRM
    assert decision.matched_rule is not None


@pytest.mark.asyncio
async def test_evaluate_warn(guard_db_session):
    """A command matching a WARN rule must emit a warning."""
    await _seed_sample_rules(guard_db_session)
    guard = CommandGuard()
    decision = await guard.evaluate(
        "curl https://example.com", "node1", guard_db_session
    )
    assert decision.level == SecurityLevel.WARN
    assert decision.matched_rule is not None


@pytest.mark.asyncio
async def test_evaluate_allow(guard_db_session):
    """A command matching an ALLOW rule must be allowed."""
    await _seed_sample_rules(guard_db_session)
    guard = CommandGuard()
    decision = await guard.evaluate("ls -la", "node1", guard_db_session)
    assert decision.level == SecurityLevel.ALLOW
    assert decision.matched_rule is not None


@pytest.mark.asyncio
async def test_no_match_defaults_to_allow(guard_db_session):
    """A command that matches no rule must default to ALLOW."""
    await _seed_sample_rules(guard_db_session)
    guard = CommandGuard()
    decision = await guard.evaluate("echo hello", "node1", guard_db_session)
    assert decision.level == SecurityLevel.ALLOW
    assert decision.matched_rule is None


@pytest.mark.asyncio
async def test_bypass_patterns_skip_confirm_but_not_block(guard_db_session):
    """bypass_patterns can skip CONFIRM, but BLOCK is never bypassed."""
    await _seed_sample_rules(guard_db_session)
    guard = CommandGuard()

    # CONFIRM bypassed — should skip to default ALLOW
    decision = await guard.evaluate(
        "sudo apt-get update",
        "node1",
        guard_db_session,
        bypass_patterns=[r"\bsudo\b"],
    )
    assert decision.level == SecurityLevel.ALLOW

    # BLOCK NOT bypassed even when pattern listed
    decision = await guard.evaluate(
        "rm -rf /home",
        "node1",
        guard_db_session,
        bypass_patterns=[r"rm\s+-rf\s+/"],
    )
    assert decision.level == SecurityLevel.BLOCK


@pytest.mark.asyncio
async def test_disabled_rule_ignored(guard_db_session):
    """Rules with enabled=False must not match any command."""
    rule = SecurityRule(
        pattern=r"echo",
        level="block",
        priority=1,
        description="Block echo",
        enabled=False,
    )
    guard_db_session.add(rule)
    await guard_db_session.commit()

    guard = CommandGuard()
    decision = await guard.evaluate("echo hello", "node1", guard_db_session)
    assert decision.level == SecurityLevel.ALLOW


@pytest.mark.asyncio
async def test_invalid_regex_skipped(guard_db_session):
    """An invalid regex pattern in the DB should be silently skipped."""
    rule = SecurityRule(
        pattern=r"[invalid",
        level="block",
        priority=1,
        description="Bad regex",
        enabled=True,
    )
    guard_db_session.add(rule)
    await guard_db_session.commit()

    guard = CommandGuard()
    decision = await guard.evaluate("anything", "node1", guard_db_session)
    assert decision.level == SecurityLevel.ALLOW


@pytest.mark.asyncio
async def test_node_specific_overrides_global(guard_db_session):
    """A node-specific rule should override a global rule with the same pattern."""
    global_rule = SecurityRule(
        pattern=r"\bsudo\b",
        level="confirm",
        priority=10,
        description="Global confirm sudo",
        enabled=True,
        node_id=None,
    )
    node_rule = SecurityRule(
        pattern=r"\bsudo\b",
        level="allow",
        priority=10,
        description="Node-specific allow sudo",
        enabled=True,
        node_id="node1",
    )
    guard_db_session.add_all([global_rule, node_rule])
    await guard_db_session.commit()

    guard = CommandGuard()
    decision = await guard.evaluate("sudo ls", "node1", guard_db_session)
    assert decision.level == SecurityLevel.ALLOW


# ---------------------------------------------------------------------------
# ConfirmTokenStore tests
# ---------------------------------------------------------------------------


def test_token_create_and_validate():
    """A freshly created token must validate successfully."""
    store = ConfirmTokenStore()
    token = store.create("sudo reboot", "node42")
    assert store.validate(token, "sudo reboot", "node42") is True


def test_token_is_one_time():
    """A token must not be valid after it has been consumed once."""
    store = ConfirmTokenStore()
    token = store.create("sudo reboot", "node42")
    assert store.validate(token, "sudo reboot", "node42") is True
    assert store.validate(token, "sudo reboot", "node42") is False


def test_token_wrong_command():
    """A token must not validate if the command differs."""
    store = ConfirmTokenStore()
    token = store.create("sudo reboot", "node42")
    assert store.validate(token, "sudo halt", "node42") is False


def test_token_wrong_node():
    """A token must not validate if the node_id differs."""
    store = ConfirmTokenStore()
    token = store.create("sudo reboot", "node42")
    assert store.validate(token, "sudo reboot", "node99") is False


def test_token_expired():
    """A token used after its TTL must not validate."""
    store = ConfirmTokenStore(ttl=0.01)  # 10 ms TTL
    token = store.create("sudo reboot", "node42")
    time.sleep(0.05)
    assert store.validate(token, "sudo reboot", "node42") is False


def test_token_store_cleanup_when_many_entries(monkeypatch):
    """Expired entries should be pruned once the store grows past the threshold."""
    store = ConfirmTokenStore(ttl=0.01)
    monkeypatch.setattr(
        "shuttle.core.security._CLEANUP_THRESHOLD",
        3,
    )
    for i in range(4):
        tok = store.create(f"cmd-{i}", "n")
        store._store[tok] = (f"cmd-{i}", "n", time.monotonic() - 1.0)
    store.create("fresh", "n")
    assert len(store._store) == 1
    assert any(v[0] == "fresh" for v in store._store.values())


@pytest.mark.asyncio
async def test_evaluate_skips_overlong_regex_pattern(guard_db_session):
    """Patterns longer than 500 chars are ignored (ReDoS guard)."""
    long_pat = "x" * 501
    guard_db_session.add(
        SecurityRule(
            pattern=long_pat,
            level="block",
            priority=1,
            enabled=True,
        )
    )
    await guard_db_session.commit()
    guard = CommandGuard()
    decision = await guard.evaluate("xxx", "node1", guard_db_session)
    assert decision.level == SecurityLevel.ALLOW


@pytest.mark.asyncio
async def test_evaluate_duplicate_pattern_prefers_node_specific(guard_db_session):
    """When two rules share a pattern, the node-scoped rule wins over global."""
    guard_db_session.add_all(
        [
            SecurityRule(
                pattern=r"^uniquepat\b",
                level="warn",
                priority=5,
                enabled=True,
                node_id=None,
            ),
            SecurityRule(
                pattern=r"^uniquepat\b",
                level="block",
                priority=5,
                enabled=True,
                node_id="node1",
            ),
        ]
    )
    await guard_db_session.commit()
    guard = CommandGuard()
    decision = await guard.evaluate("uniquepat foo", "node1", guard_db_session)
    assert decision.level == SecurityLevel.BLOCK
