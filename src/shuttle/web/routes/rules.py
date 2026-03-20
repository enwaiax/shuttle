"""Security rules management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from shuttle.db.repository import RuleRepo
from shuttle.web.deps import get_db_session
from shuttle.web.schemas import RuleCreate, RuleReorderRequest, RuleResponse, RuleUpdate

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("", response_model=list[RuleResponse])
async def list_rules(
    db: AsyncSession = Depends(get_db_session),
):
    """List all security rules ordered by priority."""
    repo = RuleRepo(db)
    rules = await repo.list_all()
    return rules


@router.post("", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    body: RuleCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """Create a new security rule."""
    repo = RuleRepo(db)
    rule = await repo.create(
        pattern=body.pattern,
        level=body.level,
        node_id=body.node_id,
        description=body.description,
        priority=body.priority,
        enabled=body.enabled,
    )
    return rule


@router.put("/{rule_id}", response_model=RuleResponse)
async def update_rule(
    rule_id: str,
    body: RuleUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    """Update an existing security rule."""
    repo = RuleRepo(db)
    rule = await repo.get_by_id(rule_id)
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")

    update_data = body.model_dump(exclude_unset=True)
    updated = await repo.update(rule_id, **update_data)
    return updated


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    rule_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """Delete a security rule."""
    repo = RuleRepo(db)
    deleted = await repo.delete(rule_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")


@router.post("/reorder", response_model=list[RuleResponse])
async def reorder_rules(
    body: RuleReorderRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Reorder security rules by reassigning priorities."""
    repo = RuleRepo(db)
    await repo.reorder(body.ids)
    rules = await repo.list_all()
    return rules
