"""API endpoints for executing actions manually."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_async_session
from ..models import Host
from ..schemas import ActionRunResponse, ExecuteActionRequest
from ..services.action_runner import execute_and_record

router = APIRouter(prefix="/hosts", tags=["actions"])


@router.post("/{host_id}/actions/{action_key}", response_model=ActionRunResponse)
async def run_action(host_id: int, action_key: str, session: AsyncSession = Depends(get_async_session)) -> Any:
    """Execute an action on a given host and record the result."""
    host = await session.get(Host, host_id)
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    # Execute action with Telegram alerts enabled so failures trigger notifications
    run = await execute_and_record(session, host, action_key, attempt=1, max_attempts=1, telegram_enabled=True)
    return run


# -----------------------------------------------------------------------------
# Unified execution endpoint
# -----------------------------------------------------------------------------

@router.post("/{host_id}/execute", response_model=ActionRunResponse)
async def execute_action(
    host_id: int,
    payload: ExecuteActionRequest,
    session: AsyncSession = Depends(get_async_session),
) -> Any:
    """Execute a user‑selected action on a given host.

    This endpoint accepts a JSON body with an ``action_key`` and an optional
    ``params`` dictionary.  It forwards the call to the driver via
    ``execute_and_record``, capturing the result in the action history.
    """
    host = await session.get(Host, host_id)
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    action_key = payload.action_key
    params = payload.params or {}
    run = await execute_and_record(
        session,
        host,
        action_key,
        attempt=1,
        max_attempts=1,
        telegram_enabled=True,
        **params,
    )
    return run
