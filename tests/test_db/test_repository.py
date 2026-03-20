"""Tests for the repository CRUD layer."""

import pytest

from shuttle.db.repository import ConfigRepo, NodeRepo, RuleRepo


@pytest.mark.asyncio
async def test_node_create_and_get(db_session):
    """Test creating a node and retrieving it by id and name."""
    repo = NodeRepo(db_session)
    node = await repo.create(
        name="repo-node",
        host="10.0.0.1",
        port=22,
        username="u",
        auth_type="password",
        encrypted_credential="enc:p",
    )
    assert node.id is not None
    assert node.name == "repo-node"

    by_id = await repo.get_by_id(node.id)
    assert by_id is not None
    assert by_id.host == "10.0.0.1"

    by_name = await repo.get_by_name("repo-node")
    assert by_name is not None
    assert by_name.id == node.id


@pytest.mark.asyncio
async def test_node_update_and_delete(db_session):
    """Test updating a node's fields and then deleting it."""
    repo = NodeRepo(db_session)
    node = await repo.create(
        name="upd-node",
        host="10.0.0.2",
        port=22,
        username="u2",
        auth_type="key",
        encrypted_credential="enc:k",
    )

    updated = await repo.update(node.id, host="10.0.0.99", status="inactive")
    assert updated is not None
    assert updated.host == "10.0.0.99"
    assert updated.status == "inactive"

    deleted = await repo.delete(node.id)
    assert deleted is True

    gone = await repo.get_by_id(node.id)
    assert gone is None


@pytest.mark.asyncio
async def test_node_list_all_with_tag_filter(db_session):
    """Test listing nodes with optional tag filter."""
    repo = NodeRepo(db_session)
    await repo.create(
        name="tag-node-1",
        host="1.1.1.1",
        port=22,
        username="u",
        auth_type="password",
        encrypted_credential="enc:p",
        tags={"env": "prod"},
    )
    await repo.create(
        name="tag-node-2",
        host="2.2.2.2",
        port=22,
        username="u",
        auth_type="password",
        encrypted_credential="enc:p",
        tags={"env": "dev"},
    )

    all_nodes = await repo.list_all()
    assert len(all_nodes) >= 2

    prod_nodes = await repo.list_all(tag="prod")
    names = [n.name for n in prod_nodes]
    assert "tag-node-1" in names
    assert "tag-node-2" not in names


@pytest.mark.asyncio
async def test_rule_create_and_ordered_list(db_session):
    """Test creating security rules and retrieving them ordered by priority."""
    node_repo = NodeRepo(db_session)
    node = await node_repo.create(
        name="rule-node",
        host="3.3.3.3",
        port=22,
        username="u",
        auth_type="password",
        encrypted_credential="enc:p",
    )

    rule_repo = RuleRepo(db_session)
    await rule_repo.create(
        pattern="pattern-c", level="warn", node_id=node.id, priority=30
    )
    await rule_repo.create(
        pattern="pattern-a", level="safe", node_id=node.id, priority=10
    )
    await rule_repo.create(
        pattern="pattern-b", level="blocked", node_id=node.id, priority=20
    )

    rules = await rule_repo.list_all(node_id=node.id)
    priorities = [r.priority for r in rules]
    assert priorities == sorted(priorities), "Rules should be sorted by priority"


@pytest.mark.asyncio
async def test_rule_reorder(db_session):
    """Test reordering rules by providing a new ordered list of IDs."""
    node_repo = NodeRepo(db_session)
    node = await node_repo.create(
        name="reorder-node",
        host="4.4.4.4",
        port=22,
        username="u",
        auth_type="password",
        encrypted_credential="enc:p",
    )

    rule_repo = RuleRepo(db_session)
    r1 = await rule_repo.create(
        pattern="pat-1", level="safe", node_id=node.id, priority=10
    )
    r2 = await rule_repo.create(
        pattern="pat-2", level="safe", node_id=node.id, priority=20
    )
    r3 = await rule_repo.create(
        pattern="pat-3", level="safe", node_id=node.id, priority=30
    )

    # Reorder: r3 first, r1 second, r2 third
    await rule_repo.reorder([r3.id, r1.id, r2.id])

    rules = await rule_repo.list_all(node_id=node.id)
    assert rules[0].id == r3.id
    assert rules[1].id == r1.id
    assert rules[2].id == r2.id


@pytest.mark.asyncio
async def test_config_get_set(db_session):
    """Test ConfigRepo upsert and retrieval."""
    repo = ConfigRepo(db_session)

    # Initially missing
    val = await repo.get("theme")
    assert val is None

    # Set it
    await repo.set("theme", {"mode": "dark"})
    val = await repo.get("theme")
    assert val == {"mode": "dark"}

    # Upsert update
    await repo.set("theme", {"mode": "light"})
    val = await repo.get("theme")
    assert val == {"mode": "light"}
