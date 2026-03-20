"""Data export/import endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shuttle.db.repository import ConfigRepo, NodeRepo, RuleRepo
from shuttle.web.deps import get_db_session
from shuttle.web.routes.nodes import _to_response
from shuttle.web.schemas import DataExport, SettingsResponse

router = APIRouter(prefix="/data", tags=["data"])


@router.post("/export", response_model=DataExport)
async def export_data(
    db: AsyncSession = Depends(get_db_session),
):
    """Export all nodes, rules, and settings."""
    node_repo = NodeRepo(db)
    rule_repo = RuleRepo(db)
    config_repo = ConfigRepo(db)

    nodes = await node_repo.list_all()
    rules = await rule_repo.list_all()
    stored_settings = await config_repo.get("settings")

    defaults = SettingsResponse()
    if stored_settings and isinstance(stored_settings, dict):
        settings = SettingsResponse(**{**defaults.model_dump(), **stored_settings})
    else:
        settings = defaults

    return DataExport(
        nodes=[_to_response(n) for n in nodes],
        rules=rules,
        settings=settings,
    )


@router.post("/import")
async def import_data(
    body: DataExport,
):
    """Import data (stub — returns counts without persisting)."""
    return {
        "status": "accepted",
        "counts": {
            "nodes": len(body.nodes),
            "rules": len(body.rules),
        },
    }
