"""API endpoints for managing hosts and executing actions."""

from __future__ import annotations

from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_session
from ..models import Host
from ..schemas import (
    HostCreate,
    HostUpdate,
    HostResponse,
    ActionRunResponse,
    HealthResponse,
)
from ..services.actions import execute_action
from ..services.health import check_host_health, check_all_hosts
from ..drivers.base import get_driver


router = APIRouter(prefix="/hosts", tags=["hosts"])


# ----------------------------
# LIST HOSTS (support /hosts and /hosts/)
# ----------------------------

@router.get("", response_model=List[HostResponse])
@router.get("/", response_model=List[HostResponse])
async def list_hosts(session: AsyncSession = Depends(get_session)) -> List[HostResponse]:
    result = await session.execute(select(Host))
    hosts = result.scalars().all()
    return [HostResponse.model_validate(h) for h in hosts]


@router.post("", response_model=HostResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=HostResponse, status_code=status.HTTP_201_CREATED)
async def create_host(host_in: HostCreate, session: AsyncSession = Depends(get_session)) -> HostResponse:
    # Build a Host instance without a port. The driver uses the default port.
    host = Host(
        name=host_in.name,
        ip=host_in.ip,
        type=host_in.type,
        username=host_in.username,
        password=host_in.password,
    )
    session.add(host)
    await session.commit()
    await session.refresh(host)
    return HostResponse.model_validate(host)


# ----------------------------
# IMPORTANT: fixed routes FIRST (avoid /{host_id} conflicts)
# ----------------------------

# ✅ Compatibility alias for older frontend that calls GET /hosts/health
@router.get("/health", response_model=List[HealthResponse])
async def health_check_all_compat(session: AsyncSession = Depends(get_session)) -> List[HealthResponse]:
    responses = await check_all_hosts(session)
    await session.commit()
    return responses


@router.get("/summary/health", response_model=List[HealthResponse])
async def health_check_all(session: AsyncSession = Depends(get_session)) -> List[HealthResponse]:
    responses = await check_all_hosts(session)
    await session.commit()
    return responses


@router.get("/summary/health-stats")
async def health_summary_stats(session: AsyncSession = Depends(get_session)) -> Dict[str, int]:
    responses = await check_all_hosts(session)
    await session.commit()

    total = len(responses)
    online = sum(1 for r in responses if getattr(r, "status", None) == "ONLINE")
    offline = sum(1 for r in responses if getattr(r, "status", None) == "OFFLINE")
    unknown = total - online - offline

    return {"total": total, "online": online, "offline": offline, "unknown": unknown}


@router.get("/{host_id}/health", response_model=HealthResponse)
async def health_check_endpoint(host_id: int, session: AsyncSession = Depends(get_session)) -> HealthResponse:
    host = await session.get(Host, host_id)
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    response = await check_host_health(session, host)
    await session.commit()
    return response


@router.get("/{host_id}/actions", response_model=Dict[str, str])
async def list_host_actions(host_id: int, session: AsyncSession = Depends(get_session)) -> Dict[str, str]:
    host = await session.get(Host, host_id)
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    driver = get_driver(host)
    return await driver.supported_actions()


@router.post("/{host_id}/execute", response_model=ActionRunResponse)
async def execute_host_action(
    host_id: int,
    request: Dict[str, Any],
    session: AsyncSession = Depends(get_session),
) -> ActionRunResponse:
    action_key = request.get("action_key")
    params = request.get("params") or {}

    if not action_key:
        raise HTTPException(status_code=400, detail="'action_key' is required")

    host = await session.get(Host, host_id)
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")

    run = await execute_action(session, host, action_key, params)
    await session.commit()
    await session.refresh(run)
    return ActionRunResponse.model_validate(run)


@router.get("/{host_id}", response_model=HostResponse)
async def get_host(host_id: int, session: AsyncSession = Depends(get_session)) -> HostResponse:
    host = await session.get(Host, host_id)
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    return HostResponse.model_validate(host)


@router.put("/{host_id}", response_model=HostResponse)
async def update_host(host_id: int, host_in: HostUpdate, session: AsyncSession = Depends(get_session)) -> HostResponse:
    host = await session.get(Host, host_id)
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")

    data = host_in.model_dump(exclude_unset=True)
    # Ignore port if provided (legacy clients); it's no longer part of the model.
    data.pop("port", None)

    for field, value in data.items():
        setattr(host, field, value)

    await session.commit()
    await session.refresh(host)
    return HostResponse.model_validate(host)


@router.delete("/{host_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_host(host_id: int, session: AsyncSession = Depends(get_session)) -> None:
    host = await session.get(Host, host_id)
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    await session.delete(host)
    await session.commit()
