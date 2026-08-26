"""Human approval queue endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shuttle.db.repository import ApprovalRepo
from shuttle.web.deps import get_db_session
from shuttle.web.schemas import ApprovalDecision, ApprovalResponse

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("", response_model=list[ApprovalResponse])
async def list_approvals(
    status: str | None = Query(
        None, pattern=r"^(pending|approved|denied|consumed|expired)$"
    ),
    db: AsyncSession = Depends(get_db_session),
):
    return await ApprovalRepo(db).list(status)


@router.get("/{approval_id}", response_model=ApprovalResponse)
async def get_approval(
    approval_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    request = await ApprovalRepo(db).get_by_id(approval_id)
    if request is None:
        raise HTTPException(404, "Approval request not found")
    return request


@router.post("/{approval_id}/decision", response_model=ApprovalResponse)
async def decide_approval(
    approval_id: str,
    body: ApprovalDecision,
    db: AsyncSession = Depends(get_db_session),
):
    request = await ApprovalRepo(db).decide(
        approval_id,
        approve=body.approve,
        approver=body.approver,
        reason=body.reason,
    )
    if request is None:
        raise HTTPException(409, "Approval is missing or no longer pending")
    return request
