"""Tests for settings API endpoints."""

import pytest


@pytest.mark.asyncio
async def test_get_settings_defaults(client):
    resp = await client.get("/api/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["pool_max_total"] == 50


@pytest.mark.asyncio
async def test_update_settings(client):
    resp = await client.put("/api/settings", json={"pool_max_total": 100})
    assert resp.status_code == 200
    assert resp.json()["pool_max_total"] == 100

    # Verify persisted
    get_resp = await client.get("/api/settings")
    assert get_resp.status_code == 200
    assert get_resp.json()["pool_max_total"] == 100
