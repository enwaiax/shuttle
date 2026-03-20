"""Dashboard statistics endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shuttle.db.models import CommandLog, Node, Session
from shuttle.web.deps import get_db_session

router = APIRouter(tags=["stats"])


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db_session)):
    """Return dashboard summary counts."""
    node_count = (await db.execute(select(func.count(Node.id)))).scalar() or 0
    active_sessions = (
        await db.execute(
            select(func.count(Session.id)).where(Session.status == "active")
        )
    ).scalar() or 0
    total_commands = (
        await db.execute(select(func.count(CommandLog.id)))
    ).scalar() or 0

    return {
        "node_count": node_count,
        "active_sessions": active_sessions,
        "total_commands": total_commands,
    }
