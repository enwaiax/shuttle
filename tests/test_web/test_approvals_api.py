"""Approval queue API tests."""

from datetime import UTC, datetime, timedelta

import pytest

from shuttle.db.repository import ApprovalRepo, NodeRepo


@pytest.mark.asyncio
async def test_pending_approval_can_only_be_decided_once(client, db_session):
    node = await NodeRepo(db_session).create(
        name="gpu-1",
        host="10.0.0.1",
        username="runner",
        encrypted_credential="enc",
    )
    request = await ApprovalRepo(db_session).create(
        node_id=node.id,
        node_name=node.name,
        action="command",
        command="sudo systemctl restart trainer",
        command_hash="a" * 64,
        actor_id="alice",
        client_id="claude-code",
        conversation_id="conv-1",
        reason="Service restart",
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )

    listed = await client.get("/api/approvals?status=pending")
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == request.id

    decided = await client.post(
        f"/api/approvals/{request.id}/decision",
        json={"approve": True, "approver": "human@example.com", "reason": "Reviewed"},
    )
    assert decided.status_code == 200
    assert decided.json()["status"] == "approved"
    assert decided.json()["approver"] == "human@example.com"

    duplicate = await client.post(
        f"/api/approvals/{request.id}/decision",
        json={"approve": False, "approver": "other@example.com"},
    )
    assert duplicate.status_code == 409


@pytest.mark.asyncio
async def test_expired_approval_cannot_be_granted(client, db_session):
    node = await NodeRepo(db_session).create(
        name="gpu-expired",
        host="10.0.0.2",
        username="runner",
        encrypted_credential="enc",
    )
    request = await ApprovalRepo(db_session).create(
        node_id=node.id,
        node_name=node.name,
        command="shutdown -h now",
        command_hash="b" * 64,
        actor_id="bob",
        client_id="codex",
        conversation_id="conv-2",
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )

    response = await client.post(
        f"/api/approvals/{request.id}/decision",
        json={"approve": True, "approver": "human@example.com"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "expired"
