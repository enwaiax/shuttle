"""Tests for the Command Logs API."""

import pytest

from shuttle.db.repository import LogRepo, NodeRepo


@pytest.mark.asyncio
async def test_list_logs_empty(client):
    resp = await client.get("/api/logs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_logs_with_data(client, db_session):
    # Seed a node and 5 logs
    node_repo = NodeRepo(db_session)
    node = await node_repo.create(
        name="log-node",
        host="10.0.0.1",
        username="root",
        auth_type="password",
        encrypted_credential="enc",
    )

    log_repo = LogRepo(db_session)
    for i in range(5):
        await log_repo.create(
            node_id=node.id,
            command=f"cmd-{i}",
            exit_code=0,
        )

    # Page 1, page_size 3
    resp = await client.get("/api/logs?page=1&page_size=3")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 3
    assert data["total"] == 5
    assert data["page"] == 1
    assert data["page_size"] == 3


@pytest.mark.asyncio
async def test_list_logs_filter_by_node(client, db_session):
    node_repo = NodeRepo(db_session)
    node_a = await node_repo.create(
        name="node-a",
        host="10.0.0.1",
        username="root",
        auth_type="password",
        encrypted_credential="enc",
    )
    node_b = await node_repo.create(
        name="node-b",
        host="10.0.0.2",
        username="root",
        auth_type="password",
        encrypted_credential="enc",
    )

    log_repo = LogRepo(db_session)
    await log_repo.create(node_id=node_a.id, command="ls")
    await log_repo.create(node_id=node_b.id, command="pwd")

    # Filter by node_a
    resp = await client.get(f"/api/logs?node_id={node_a.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["node_name"] == "node-a"
    assert data["items"][0]["command"] == "ls"
