"""Tests for data export/import API endpoints."""

import pytest


@pytest.mark.asyncio
async def test_export_empty(client):
    resp = await client.post("/api/data/export")
    assert resp.status_code == 200
    data = resp.json()
    assert data["nodes"] == []
    assert data["rules"] == []


@pytest.mark.asyncio
async def test_export_import_roundtrip(client):
    # Create a node
    node_resp = await client.post(
        "/api/nodes",
        json={
            "name": "test-node",
            "host": "192.168.1.1",
            "port": 22,
            "username": "admin",
            "auth_type": "password",
            "credential": "secret",
        },
    )
    assert node_resp.status_code == 201

    # Create a rule
    rule_resp = await client.post(
        "/api/rules",
        json={"pattern": "rm -rf .*", "level": "block"},
    )
    assert rule_resp.status_code == 201

    # Export
    export_resp = await client.post("/api/data/export")
    assert export_resp.status_code == 200
    export_data = export_resp.json()
    assert len(export_data["nodes"]) == 1
    assert len(export_data["rules"]) == 1

    # Import (stub)
    import_resp = await client.post("/api/data/import", json=export_data)
    assert import_resp.status_code == 200
    import_data = import_resp.json()
    assert import_data["counts"]["nodes"] == 1
    assert import_data["counts"]["rules"] == 1
