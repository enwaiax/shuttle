"""Test effective rules endpoint (global + per-node merged)."""

import pytest
from shuttle.db.repository import NodeRepo, RuleRepo


@pytest.mark.asyncio
async def test_effective_rules_inherits_global(client, db_session):
    node_repo = NodeRepo(db_session)
    node = await node_repo.create(name="eff-node", host="10.0.0.1", username="u",
                                   auth_type="password", encrypted_credential="x")
    rule_repo = RuleRepo(db_session)
    await rule_repo.create(pattern="sudo .*", level="confirm", priority=10)
    await db_session.commit()

    resp = await client.get(f"/api/rules/effective/{node.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert any(r["pattern"] == "sudo .*" for r in data)


@pytest.mark.asyncio
async def test_effective_rules_node_override(client, db_session):
    node_repo = NodeRepo(db_session)
    node = await node_repo.create(name="ovr-node", host="10.0.0.2", username="u",
                                   auth_type="password", encrypted_credential="x")
    rule_repo = RuleRepo(db_session)
    global_rule = await rule_repo.create(pattern="sudo .*", level="confirm", priority=10)
    await rule_repo.create(pattern="sudo .*", level="allow", priority=10,
                           node_id=node.id, source_rule_id=global_rule.id)
    await db_session.commit()

    resp = await client.get(f"/api/rules/effective/{node.id}")
    data = resp.json()
    sudo_rules = [r for r in data if r["pattern"] == "sudo .*"]
    assert len(sudo_rules) == 1
    assert sudo_rules[0]["level"] == "allow"


@pytest.mark.asyncio
async def test_effective_rules_node_not_found(client):
    resp = await client.get("/api/rules/effective/nonexistent")
    assert resp.status_code == 404
