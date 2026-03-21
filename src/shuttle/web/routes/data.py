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
    db: AsyncSession = Depends(get_db_session),
):
    """Import nodes, rules, and settings from an exported JSON payload."""
    node_repo = NodeRepo(db)
    rule_repo = RuleRepo(db)
    config_repo = ConfigRepo(db)

    node_count = 0
    for n in body.nodes:
        existing = await node_repo.get_by_name(n.name)
        if existing is not None:
            continue
        await node_repo.create(
            name=n.name,
            host=n.host,
            port=n.port,
            username=n.username,
            auth_type=n.auth_type,
            jump_host_id=n.jump_host_id,
            tags=n.tags,
        )
        node_count += 1

    rule_count = 0
    for r in body.rules:
        await rule_repo.create(
            pattern=r.pattern,
            level=r.level,
            node_id=r.node_id,
            description=r.description,
            priority=r.priority,
            enabled=r.enabled,
        )
        rule_count += 1

    settings_dict = body.settings.model_dump()
    settings_count = 0
    for key, value in settings_dict.items():
        await config_repo.set(key, value)
        settings_count += 1

    return {
        "status": "accepted",
        "counts": {
            "nodes": node_count,
            "rules": rule_count,
            "settings": settings_count,
        },
        "message": f"Imported {node_count} nodes, {rule_count} rules, {settings_count} settings",
    }
