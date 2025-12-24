"""API endpoints for listing and retrieving action runs."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_session
from ..models import ActionRun, ActionStatus
from ..schemas import ActionRunResponse


router = APIRouter(prefix="/action-runs", tags=["action_runs"])


@router.get("/", response_model=List[ActionRunResponse])
async def list_runs(
    session: AsyncSession = Depends(get_session),
    host_id: Optional[int] = None,
    action_key: Optional[str] = None,
    status: Optional[ActionStatus] = Query(default=None),
    start: Optional[datetime] = Query(default=None, description="Start timestamp for filtering"),
    end: Optional[datetime] = Query(default=None, description="End timestamp for filtering"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> List[ActionRunResponse]:
    conditions = []
    if host_id is not None:
        conditions.append(ActionRun.host_id == host_id)
    if action_key is not None:
        conditions.append(ActionRun.action_key == action_key)
    if status is not None:
        conditions.append(ActionRun.status == status)
    if start is not None:
        conditions.append(ActionRun.executed_at >= start)
    if end is not None:
        conditions.append(ActionRun.executed_at <= end)
    query = select(ActionRun)
    if conditions:
        query = query.where(and_(*conditions))
    query = query.order_by(ActionRun.executed_at.desc()).offset(offset).limit(limit)
    result = await session.execute(query)
    runs = result.scalars().all()
    return [ActionRunResponse.model_validate(run) for run in runs]


@router.get("/{run_id}", response_model=ActionRunResponse)
async def get_run(run_id: int, session: AsyncSession = Depends(get_session)) -> ActionRunResponse:
    run = await session.get(ActionRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Action run not found")
    return ActionRunResponse.model_validate(run)