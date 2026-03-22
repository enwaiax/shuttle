"""Tests for SessionRepo, LogRepo, cleanup_old_data, and repository edge cases."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from shuttle.db.repository import (
    LogRepo,
    NodeRepo,
    RuleRepo,
    SessionRepo,
    cleanup_old_data,
)


@pytest.mark.asyncio
async def test_node_update_and_delete_missing_returns_none_or_false(db_session):
    repo = NodeRepo(db_session)
    assert await repo.update("00000000-0000-0000-0000-000000000000", host="x") is None
    assert await repo.delete("00000000-0000-0000-0000-000000000000") is False


@pytest.mark.asyncio
async def test_rule_update_delete_missing(db_session):
    repo = RuleRepo(db_session)
    assert (
        await repo.update("00000000-0000-0000-0000-000000000000", level="allow") is None
    )
    assert await repo.delete("00000000-0000-0000-0000-000000000000") is False


@pytest.mark.asyncio
async def test_rule_list_effective_merges_global_and_node_rules(db_session):
    node_repo = NodeRepo(db_session)
    node = await node_repo.create(
        name="eff-node",
        host="1.1.1.1",
        port=22,
        username="u",
        auth_type="password",
        encrypted_credential="e",
    )
    rrepo = RuleRepo(db_session)
    await rrepo.create(pattern=r"^g\d$", level="warn", priority=1, node_id=None)
    await rrepo.create(pattern=r"^n\d$", level="block", priority=2, node_id=node.id)
    await rrepo.create(pattern=r"^g\d$", level="allow", priority=3, node_id=node.id)
    merged = await rrepo.list_effective(node.id)
    patterns = {x.pattern for x in merged}
    assert r"^n\d$" in patterns
    assert r"^g\d$" in patterns


@pytest.mark.asyncio
async def test_rule_reorder_skips_unknown_id(db_session):
    rrepo = RuleRepo(db_session)
    r = await rrepo.create(pattern="p", level="allow", priority=0)
    await rrepo.reorder([r.id, "not-a-real-uuid"])
    again = await rrepo.get_by_id(r.id)
    assert again is not None
    assert again.priority == 0


@pytest.mark.asyncio
async def test_session_repo_lifecycle(db_session):
    node_repo = NodeRepo(db_session)
    node = await node_repo.create(
        name="s-node",
        host="2.2.2.2",
        port=22,
        username="u",
        auth_type="password",
        encrypted_credential="e",
    )
    srepo = SessionRepo(db_session)
    sess = await srepo.create(node_id=node.id, working_directory="/tmp")
    assert sess.status == "active"
    listed = await srepo.list_active()
    assert any(x.id == sess.id for x in listed)
    updated = await srepo.update_working_dir(sess.id, "/var")
    assert updated is not None
    assert updated.working_directory == "/var"
    closed = await srepo.close(sess.id)
    assert closed is not None
    assert closed.status == "closed"
    assert await srepo.close("bad-id") is None
    assert (
        await srepo.update_working_dir("00000000-0000-0000-0000-000000000000", "/tmp")
        is None
    )


@pytest.mark.asyncio
async def test_log_repo_list_by_session(db_session):
    node_repo = NodeRepo(db_session)
    node = await node_repo.create(
        name="l-node",
        host="3.3.3.3",
        port=22,
        username="u",
        auth_type="password",
        encrypted_credential="e",
    )
    srepo = SessionRepo(db_session)
    sess = await srepo.create(node_id=node.id)
    lrepo = LogRepo(db_session)
    await lrepo.create(
        node_id=node.id,
        command="ls",
        session_id=sess.id,
        exit_code=0,
    )
    logs = await lrepo.list_by_session(sess.id, limit=10, offset=0)
    assert len(logs) == 1
    assert logs[0].command == "ls"


@pytest.mark.asyncio
async def test_cleanup_old_data_deletes_stale_rows(db_session):
    node_repo = NodeRepo(db_session)
    node = await node_repo.create(
        name="c-node",
        host="4.4.4.4",
        port=22,
        username="u",
        auth_type="password",
        encrypted_credential="e",
    )
    lrepo = LogRepo(db_session)
    log = await lrepo.create(node_id=node.id, command="old", exit_code=0)
    log.executed_at = datetime.now(UTC) - timedelta(days=400)
    await db_session.commit()

    srepo = SessionRepo(db_session)
    sess = await srepo.create(node_id=node.id)
    await srepo.close(sess.id)
    row = await srepo.get_by_id(sess.id)
    row.closed_at = datetime.now(UTC) - timedelta(days=400)
    await db_session.commit()

    counts = await cleanup_old_data(
        db_session, command_log_days=30, closed_session_days=7
    )
    assert counts["command_logs"] >= 1
    assert counts["sessions"] >= 1
