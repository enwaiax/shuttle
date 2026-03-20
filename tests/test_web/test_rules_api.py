"""Tests for security rules API endpoints."""

import pytest


@pytest.mark.asyncio
async def test_list_rules_empty(client):
    resp = await client.get("/api/rules")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_rule(client):
    resp = await client.post(
        "/api/rules",
        json={
            "pattern": "sudo .*",
            "level": "confirm",
            "description": "Require confirm for sudo",
            "priority": 10,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["pattern"] == "sudo .*"
    assert data["level"] == "confirm"
    assert data["description"] == "Require confirm for sudo"
    assert data["priority"] == 10
    assert "id" in data


@pytest.mark.asyncio
async def test_update_rule(client):
    # Create a rule first
    create_resp = await client.post(
        "/api/rules",
        json={"pattern": "rm -rf .*", "level": "confirm"},
    )
    assert create_resp.status_code == 201
    rule_id = create_resp.json()["id"]

    # Update the level
    update_resp = await client.put(
        f"/api/rules/{rule_id}",
        json={"level": "block"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["level"] == "block"
    assert update_resp.json()["pattern"] == "rm -rf .*"


@pytest.mark.asyncio
async def test_delete_rule(client):
    # Create a rule first
    create_resp = await client.post(
        "/api/rules",
        json={"pattern": "shutdown .*", "level": "block"},
    )
    assert create_resp.status_code == 201
    rule_id = create_resp.json()["id"]

    # Delete the rule
    delete_resp = await client.delete(f"/api/rules/{rule_id}")
    assert delete_resp.status_code == 204

    # Verify it's gone
    list_resp = await client.get("/api/rules")
    assert all(r["id"] != rule_id for r in list_resp.json())


@pytest.mark.asyncio
async def test_reorder_rules(client):
    # Create 3 rules (a, b, c)
    ids = []
    for pattern in ["rule_a", "rule_b", "rule_c"]:
        resp = await client.post(
            "/api/rules",
            json={"pattern": pattern, "level": "allow", "priority": 0},
        )
        assert resp.status_code == 201
        ids.append(resp.json()["id"])

    # Reverse the order
    reversed_ids = list(reversed(ids))
    reorder_resp = await client.post(
        "/api/rules/reorder",
        json={"ids": reversed_ids},
    )
    assert reorder_resp.status_code == 200

    # Verify new order
    list_resp = await client.get("/api/rules")
    returned_ids = [r["id"] for r in list_resp.json()]
    assert returned_ids == reversed_ids
