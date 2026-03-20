"""Full test suite for the Nodes CRUD API."""

import pytest


NODE_PAYLOAD = {
    "name": "test-node",
    "host": "192.168.1.1",
    "port": 22,
    "username": "root",
    "auth_type": "password",
    "credential": "secret123",
}


@pytest.mark.asyncio
async def test_list_nodes_empty(client):
    resp = await client.get("/api/nodes")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_node(client):
    resp = await client.post("/api/nodes", json=NODE_PAYLOAD)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "test-node"
    assert data["host"] == "192.168.1.1"
    assert data["port"] == 22
    assert data["username"] == "root"
    assert data["auth_type"] == "password"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_create_node_duplicate_name(client):
    await client.post("/api/nodes", json=NODE_PAYLOAD)
    resp = await client.post("/api/nodes", json=NODE_PAYLOAD)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_node(client):
    create_resp = await client.post("/api/nodes", json=NODE_PAYLOAD)
    node_id = create_resp.json()["id"]

    resp = await client.get(f"/api/nodes/{node_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == node_id
    assert resp.json()["name"] == "test-node"


@pytest.mark.asyncio
async def test_get_node_not_found(client):
    resp = await client.get("/api/nodes/nonexistent-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_node(client):
    create_resp = await client.post("/api/nodes", json=NODE_PAYLOAD)
    node_id = create_resp.json()["id"]

    resp = await client.put(f"/api/nodes/{node_id}", json={"host": "10.0.0.1"})
    assert resp.status_code == 200
    assert resp.json()["host"] == "10.0.0.1"
    assert resp.json()["name"] == "test-node"  # unchanged


@pytest.mark.asyncio
async def test_delete_node(client):
    create_resp = await client.post("/api/nodes", json=NODE_PAYLOAD)
    node_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/nodes/{node_id}")
    assert resp.status_code == 204

    # Confirm it's gone
    resp = await client.get(f"/api/nodes/{node_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_nodes_with_tag_filter(client):
    prod_payload = {**NODE_PAYLOAD, "name": "prod-node", "tags": ["prod"]}
    dev_payload = {**NODE_PAYLOAD, "name": "dev-node", "tags": ["dev"]}

    await client.post("/api/nodes", json=prod_payload)
    await client.post("/api/nodes", json=dev_payload)

    # Filter by tag=prod
    resp = await client.get("/api/nodes?tag=prod")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "prod-node"

    # All nodes
    resp = await client.get("/api/nodes")
    assert resp.status_code == 200
    assert len(resp.json()) == 2
