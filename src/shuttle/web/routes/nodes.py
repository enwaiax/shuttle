"""Nodes CRUD API endpoints."""

import tempfile
import time
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from shuttle.core.credentials import CredentialManager
from shuttle.db.repository import NodeRepo
from shuttle.web.deps import get_db_session
from shuttle.web.schemas import NodeCreate, NodeResponse, NodeTestResult, NodeUpdate

router = APIRouter(tags=["nodes"])

_cred_mgr: CredentialManager | None = None


def _get_cred_mgr() -> CredentialManager:
    """Return a singleton CredentialManager, creating a temp dir if needed."""
    global _cred_mgr
    if _cred_mgr is None:
        shuttle_dir = Path.home() / ".shuttle"
        if not shuttle_dir.exists():
            shuttle_dir = Path(tempfile.mkdtemp(prefix="shuttle_"))
        _cred_mgr = CredentialManager(shuttle_dir)
    return _cred_mgr


def _to_response(node) -> dict:
    """Convert an ORM Node to a response dict."""
    tags = node.tags
    # tags is stored as JSON (could be list or dict); normalize to list
    if isinstance(tags, dict):
        tags = list(tags.values())
    elif tags is None:
        tags = None
    return {
        "id": node.id,
        "name": node.name,
        "host": node.host,
        "port": node.port,
        "username": node.username,
        "auth_type": node.auth_type,
        "jump_host_id": node.jump_host_id,
        "tags": tags,
        "status": node.status,
        "created_at": node.created_at,
        "updated_at": node.updated_at,
    }


@router.get("/nodes", response_model=list[NodeResponse])
async def list_nodes(
    tag: str | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    """List all nodes, optionally filtered by tag."""
    repo = NodeRepo(db)
    nodes = await repo.list_all(tag=tag)
    return [_to_response(n) for n in nodes]


@router.post("/nodes", response_model=NodeResponse, status_code=status.HTTP_201_CREATED)
async def create_node(
    body: NodeCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """Create a new node."""
    repo = NodeRepo(db)

    # Check for duplicate name
    existing = await repo.get_by_name(body.name)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Node with name '{body.name}' already exists",
        )

    cred_mgr = _get_cred_mgr()
    encrypted = cred_mgr.encrypt(body.credential)

    node = await repo.create(
        name=body.name,
        host=body.host,
        port=body.port,
        username=body.username,
        auth_type=body.auth_type,
        encrypted_credential=encrypted,
        jump_host_id=body.jump_host_id,
        tags=body.tags,
    )
    return _to_response(node)


@router.get("/nodes/{node_id}", response_model=NodeResponse)
async def get_node(
    node_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """Get a single node by ID."""
    repo = NodeRepo(db)
    node = await repo.get_by_id(node_id)
    if node is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    return _to_response(node)


@router.put("/nodes/{node_id}", response_model=NodeResponse)
async def update_node(
    node_id: str,
    body: NodeUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    """Update an existing node."""
    repo = NodeRepo(db)
    node = await repo.get_by_id(node_id)
    if node is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")

    update_data = body.model_dump(exclude_unset=True)

    # Encrypt credential if provided
    if "credential" in update_data:
        cred_mgr = _get_cred_mgr()
        update_data["encrypted_credential"] = cred_mgr.encrypt(update_data.pop("credential"))

    updated = await repo.update(node_id, **update_data)
    return _to_response(updated)


@router.delete("/nodes/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_node(
    node_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """Delete a node by ID."""
    repo = NodeRepo(db)
    deleted = await repo.delete(node_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")


@router.post("/nodes/{node_id}/test", response_model=NodeTestResult)
async def test_node(
    node_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """Test SSH connectivity for a node."""
    repo = NodeRepo(db)
    node = await repo.get_by_id(node_id)
    if node is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")

    try:
        from shuttle.core.proxy import NodeConnectInfo, connect_ssh

        cred_mgr = _get_cred_mgr()
        credential = cred_mgr.decrypt(node.encrypted_credential)

        info = NodeConnectInfo(
            node_id=node.id,
            hostname=node.host,
            port=node.port,
            username=node.username,
            password=credential if node.auth_type == "password" else None,
            private_key=credential if node.auth_type == "key" else None,
        )

        start = time.monotonic()
        client = await connect_ssh(info)
        latency = (time.monotonic() - start) * 1000
        client.close()

        # Persist latency + last_seen to DB
        from datetime import datetime, timezone
        await repo.update(node_id, {
            "latency_ms": int(latency),
            "last_seen_at": datetime.now(timezone.utc),
            "status": "active",
        })

        return NodeTestResult(success=True, message=f"Connection successful ({int(latency)}ms)", latency_ms=latency)
    except Exception as exc:
        await repo.update(node_id, {"status": "offline"})
        return NodeTestResult(success=False, message=str(exc))
