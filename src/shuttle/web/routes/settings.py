"""Settings management endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shuttle.db.repository import ConfigRepo
from shuttle.web.deps import get_db_session
from shuttle.web.schemas import SettingsResponse, SettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])

SETTINGS_KEY = "settings"


@router.get("", response_model=SettingsResponse)
async def get_settings(
    db: AsyncSession = Depends(get_db_session),
):
    """Return current settings, merged with defaults."""
    repo = ConfigRepo(db)
    stored = await repo.get(SETTINGS_KEY)
    defaults = SettingsResponse()
    if stored and isinstance(stored, dict):
        return SettingsResponse(**{**defaults.model_dump(), **stored})
    return defaults


@router.put("", response_model=SettingsResponse)
async def update_settings(
    body: SettingsUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    """Update settings, merging with existing values."""
    repo = ConfigRepo(db)
    stored = await repo.get(SETTINGS_KEY)
    defaults = SettingsResponse()

    current = defaults.model_dump()
    if stored and isinstance(stored, dict):
        current.update(stored)

    updates = body.model_dump(exclude_unset=True)
    current.update(updates)

    await repo.set(SETTINGS_KEY, current)
    return SettingsResponse(**current)
