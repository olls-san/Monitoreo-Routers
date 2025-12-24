"""API endpoints for retrieving action run history."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_async_session
from ..models import ActionRun
from ..schemas import ActionRunResponse

# Use the canonical prefix "/action-runs" for history endpoints.  The
# previous implementation used "/runs" which conflicted with the new
# contract.  Keep both prefixes by mounting the router twice in
# ``app/main.py`` if backwards compatibility is required.  Here we
# define the router with the new prefix.  ``app/main.py`` will still
# include this router once, so the prefix must match the desired
# contract.
router = APIRouter(prefix="/action-runs", tags=["history"])


@router.get("/", response_model=List[ActionRunResponse])
async def list_runs(
    host_id: Optional[int] = Query(None),
    action_key: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_async_session),
) -> List[ActionRun]:
    """List action runs with optional filters."""
    query = select(ActionRun)
    if host_id is not None:
        query = query.where(ActionRun.host_id == host_id)
    if action_key is not None:
        query = query.where(ActionRun.action_key == action_key)
    if status is not None:
        query = query.where(ActionRun.status == status)
    result = await session.execute(query)
    runs = result.scalars().all()
    return runs
