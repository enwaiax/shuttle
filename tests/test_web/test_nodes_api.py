"""Node API endpoint tests."""

import pytest


@pytest.mark.asyncio
async def test_app_starts(client):
    """Smoke test: /api/stats returns 200."""
    resp = await client.get("/api/stats")
    assert resp.status_code == 200
