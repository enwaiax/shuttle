"""Tests for the Sessions API."""

import pytest

from shuttle.db.repository import NodeRepo, SessionRepo


@pytest.mark.asyncio
async def test_list_sessions_empty(client):
    resp = await client.get("/api/sessions")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_and_close_session(client, db_session):
    # Seed a node and session
    node_repo = NodeRepo(db_session)
    node = await node_repo.create(
        name="sess-node",
        host="10.0.0.1",
        username="root",
        auth_type="password",
        encrypted_credential="enc",
    )

    session_repo = SessionRepo(db_session)
    sess = await session_repo.create(
        node_id=node.id, working_directory="/home"
    )

    # List sessions
    resp = await client.get("/api/sessions")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == sess.id
    assert data[0]["node_name"] == "sess-node"
    assert data[0]["status"] == "active"

    # Close session
    resp = await client.delete(f"/api/sessions/{sess.id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "closed"
    assert resp.json()["closed_at"] is not None

    # Verify via detail endpoint
    resp = await client.get(f"/api/sessions/{sess.id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "closed"


@pytest.mark.asyncio
async def test_session_not_found(client):
    resp = await client.get("/api/sessions/nonexistent")
    assert resp.status_code == 404
