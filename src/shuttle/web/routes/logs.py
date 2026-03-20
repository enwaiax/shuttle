"""Command log API endpoints."""

import csv
import io
from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shuttle.db.models import CommandLog, Node
from shuttle.web.deps import get_db_session
from shuttle.web.schemas import CommandLogResponse, LogListResponse

router = APIRouter(tags=["logs"])


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


def _log_to_response(log: CommandLog, node_names: dict[str, str]) -> dict:
    return {
        "id": log.id,
        "session_id": log.session_id,
        "node_id": log.node_id,
        "node_name": node_names.get(log.node_id),
        "command": log.command,
        "exit_code": log.exit_code,
        "stdout": log.stdout,
        "stderr": log.stderr,
        "security_level": log.security_level,
        "bypassed": log.bypassed,
        "duration_ms": log.duration_ms,
        "executed_at": log.executed_at,
    }


def _build_filter_stmt(stmt, node_id: str | None, session_id: str | None):
    """Apply optional filters to a select statement."""
    if node_id is not None:
        stmt = stmt.where(CommandLog.node_id == node_id)
    if session_id is not None:
        stmt = stmt.where(CommandLog.session_id == session_id)
    return stmt


@router.get("/logs", response_model=LogListResponse)
async def list_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    node_id: str | None = None,
    session_id: str | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    """Paginated list of command logs with optional filters."""
    # Total count
    count_stmt = select(func.count(CommandLog.id))
    count_stmt = _build_filter_stmt(count_stmt, node_id, session_id)
    total = (await db.execute(count_stmt)).scalar_one()

    # Paginated items
    items_stmt = (
        select(CommandLog)
        .order_by(CommandLog.executed_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items_stmt = _build_filter_stmt(items_stmt, node_id, session_id)
    result = await db.execute(items_stmt)
    logs = list(result.scalars().all())

    node_ids = {log.node_id for log in logs}
    node_names = await _batch_node_names(db, node_ids)

    return LogListResponse(
        items=[_log_to_response(log, node_names) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/logs/export")
async def export_logs(
    format: Literal["json", "csv"] = "json",
    node_id: str | None = None,
    session_id: str | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    """Export all matching logs as JSON or CSV."""
    stmt = select(CommandLog).order_by(CommandLog.executed_at.desc())
    stmt = _build_filter_stmt(stmt, node_id, session_id)
    result = await db.execute(stmt)
    logs = list(result.scalars().all())

    node_ids = {log.node_id for log in logs}
    node_names = await _batch_node_names(db, node_ids)

    items = [_log_to_response(log, node_names) for log in logs]

    if format == "csv":
        output = io.StringIO()
        if items:
            writer = csv.DictWriter(output, fieldnames=list(items[0].keys()))
            writer.writeheader()
            for item in items:
                # Convert datetime objects to ISO strings for CSV
                row = {
                    k: v.isoformat() if hasattr(v, "isoformat") else v
                    for k, v in item.items()
                }
                writer.writerow(row)
        content = output.getvalue()
        return StreamingResponse(
            iter([content]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=logs.csv"},
        )

    # JSON format
    # Convert datetimes to ISO strings for JSON serialization
    json_items = []
    for item in items:
        json_item = {
            k: v.isoformat() if hasattr(v, "isoformat") else v
            for k, v in item.items()
        }
        json_items.append(json_item)

    return json_items
