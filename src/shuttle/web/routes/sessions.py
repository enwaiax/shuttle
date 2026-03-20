"""Sessions management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shuttle.db.models import Node, Session
from shuttle.db.repository import SessionRepo
from shuttle.web.deps import get_db_session
from shuttle.web.schemas import SessionResponse

router = APIRouter(tags=["sessions"])


async def _batch_node_names(
    db: AsyncSession, node_ids: set[str]
) -> dict[str, str]:
    """Load node names for a set of node IDs."""
    if not node_ids:
        return {}
    result = await db.execute(
        select(Node.id, Node.name).where(Node.id.in_(node_ids))
    )
    return {row.id: row.name for row in result.all()}


def _session_to_response(sess: Session, node_names: dict[str, str]) -> dict:
    return {
        "id": sess.id,
        "node_id": sess.node_id,
        "node_name": node_names.get(sess.node_id),
        "working_directory": sess.working_directory,
        "status": sess.status,
        "created_at": sess.created_at,
        "closed_at": sess.closed_at,
    }


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(
    status_filter: str | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    """List sessions, optionally filtered by status."""
    stmt = select(Session).order_by(Session.created_at.desc())
    if status_filter is not None:
        stmt = stmt.where(Session.status == status_filter)
    result = await db.execute(stmt)
    sessions = list(result.scalars().all())

    node_ids = {s.node_id for s in sessions}
    node_names = await _batch_node_names(db, node_ids)

    return [_session_to_response(s, node_names) for s in sessions]


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """Get a single session by ID."""
    repo = SessionRepo(db)
    sess = await repo.get_by_id(session_id)
    if sess is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )
    node_names = await _batch_node_names(db, {sess.node_id})
    return _session_to_response(sess, node_names)


@router.delete("/sessions/{session_id}", response_model=SessionResponse)
async def close_session(
    session_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """Close (soft-delete) a session."""
    repo = SessionRepo(db)
    sess = await repo.close(session_id)
    if sess is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )
    node_names = await _batch_node_names(db, {sess.node_id})
    return _session_to_response(sess, node_names)
