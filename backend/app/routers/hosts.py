"""API endpoints for managing hosts (routers)."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_async_session
from ..models import Host, HostHealth, ActionRun
from ..drivers import get_driver
from ..schemas import HostCreate, HostResponse, HostUpdate
from ..schemas import HostHealthResponse, ActionRunResponse


router = APIRouter(prefix="/hosts", tags=["hosts"])


# ----------------------------
# Helpers
# ----------------------------

_TPLINK_KEYS = {"TPLINK", "TP-LINK", "OPENWRT", "TP_LINK_OPENWRT_SSH", "TP-LINK_OPENWRT_SSH"}
_MIKROTIK_KEYS = {"MIKROTIK", "MIKROTIK_REST", "MIKROTIK_ROUTEROS", "MIKROTIK_ROUTEROS_REST"}


def _normalize_router_type_and_port(data: dict) -> dict:
    """Normalize router_type (aliases -> canonical) and default ports."""
    rt = str(data.get("router_type") or "").strip().upper()

    if rt in _TPLINK_KEYS:
        data["router_type"] = "TP_LINK_OPENWRT_SSH"
        # TP-Link/OpenWrt uses SSH: 22
        if not data.get("port") or data.get("port") == 80:
            data["port"] = 22

    elif rt in _MIKROTIK_KEYS:
        data["router_type"] = "MIKROTIK_ROUTEROS_REST"
        # Mikrotik REST (si quieres forzarlo, déjalo; si no, no lo toques)
        # if not data.get("port"):
        #     data["port"] = 80

    return data


# ----------------------------
# Hosts list
# ----------------------------

@router.get("/", response_model=List[HostResponse])
async def list_hosts(session: AsyncSession = Depends(get_async_session)) -> List[dict]:
    """List hosts including a lightweight 'last action' summary."""

    last_run_sq = (
        select(ActionRun.host_id, func.max(ActionRun.started_at).label("max_started_at"))
        .group_by(ActionRun.host_id)
        .subquery()
    )

    q = (
        select(
            Host,
            ActionRun.action_key,
            ActionRun.started_at,
            ActionRun.status,
        )
        .outerjoin(last_run_sq, Host.id == last_run_sq.c.host_id)
        .outerjoin(
            ActionRun,
            (ActionRun.host_id == Host.id) & (ActionRun.started_at == last_run_sq.c.max_started_at),
        )
        .order_by(Host.id.asc())
    )

    result = await session.execute(q)
    rows = result.all()

    payload: list[dict] = []
    for host, last_action_key, last_action_at, last_action_status in rows:
        d = HostResponse.model_validate(host).model_dump()

        # cache de health del Host
        d["last_latency_ms"] = host.last_latency_ms
        d["last_check_at"] = host.last_checked_at
        # IMPORTANTE: en tu sistema guardas "online"/"offline" (minúsculas)
        d["last_online"] = (host.last_status == "online") if host.last_status else None

        # last action derivado
        d["last_action_key"] = last_action_key
        d["last_action_at"] = last_action_at
        d["last_action_status"] = last_action_status
        payload.append(d)

    return payload


# -----------------------------------------------------------------------------
# Trailing slash aliases
# -----------------------------------------------------------------------------

@router.get("", response_model=List[HostResponse])
async def list_hosts_alias(session: AsyncSession = Depends(get_async_session)) -> List[Host]:
    """Alias for ``/hosts/`` to avoid 307 redirects on ``/hosts``."""
    return await list_hosts(session)


@router.post("", response_model=HostResponse, status_code=status.HTTP_201_CREATED)
async def create_host_alias(payload: HostCreate, session: AsyncSession = Depends(get_async_session)) -> Host:
    """Alias for ``/hosts/`` POST to avoid 307 redirects on ``/hosts``."""
    return await create_host(payload, session)


# ----------------------------
# CRUD
# ----------------------------

@router.post("/", response_model=HostResponse, status_code=status.HTTP_201_CREATED)
async def create_host(payload: HostCreate, session: AsyncSession = Depends(get_async_session)) -> Host:
    data = payload.model_dump()
    data = _normalize_router_type_and_port(data)

    host = Host(**data)
    session.add(host)
    await session.commit()
    await session.refresh(host)
    return host


@router.get("/{host_id}", response_model=HostResponse)
async def get_host(host_id: int, session: AsyncSession = Depends(get_async_session)) -> Host:
    host = await session.get(Host, host_id)
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    return host


@router.put("/{host_id}", response_model=HostResponse)
async def update_host(host_id: int, payload: HostUpdate, session: AsyncSession = Depends(get_async_session)) -> Host:
    host = await session.get(Host, host_id)
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")

    updates = payload.model_dump(exclude_unset=True)

    # aplicar updates
    for field, value in updates.items():
        setattr(host, field, value)

    # si cambió router_type o port, normalizamos
    if "router_type" in updates or "port" in updates:
        normalized = _normalize_router_type_and_port(
            {
                "router_type": host.router_type,
                "port": host.port,
            }
        )
        host.router_type = normalized["router_type"]
        host.port = normalized.get("port", host.port)

    await session.commit()
    await session.refresh(host)
    return host


@router.delete("/{host_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_host(host_id: int, session: AsyncSession = Depends(get_async_session)) -> None:
    host = await session.get(Host, host_id)
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    await session.delete(host)
    await session.commit()


# ----------------------------
# Actions available per host (driver-based)
# ----------------------------

@router.get("/{host_id}/actions", response_model=List[str])
async def list_host_actions(host_id: int, session: AsyncSession = Depends(get_async_session)) -> List[str]:
    host = await session.get(Host, host_id)
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    driver = get_driver(host.router_type)
    return driver.list_supported_actions()


# -----------------------------------------------------------------------------
# Health and history endpoints
# -----------------------------------------------------------------------------

@router.get("/summary/health")
async def health_list(session: AsyncSession = Depends(get_async_session)) -> list[dict[str, object]]:
    """Return per-host health information."""
    result = await session.execute(select(Host))
    hosts = result.scalars().all()

    health_data: list[dict[str, object]] = []
    for host in hosts:
        if host.last_status is None:
            online = None
        else:
            online = host.last_status == "online"

        health_data.append(
            {
                "host_id": host.id,
                "online": online,
                "latency_ms": host.last_latency_ms,
                "checked_at": host.last_checked_at,
            }
        )
    return health_data


@router.get("/summary/health-stats")
async def health_stats(session: AsyncSession = Depends(get_async_session)) -> dict[str, int]:
    """Return aggregated host status counts."""
    total = (await session.execute(select(func.count()).select_from(Host))).scalar_one()
    online = (
        await session.execute(select(func.count()).select_from(Host).where(Host.last_status == "online"))
    ).scalar_one()
    offline = (
        await session.execute(select(func.count()).select_from(Host).where(Host.last_status == "offline"))
    ).scalar_one()
    unknown = total - online - offline
    return {"total": total, "online": online, "offline": offline, "unknown": unknown}


@router.get("/{host_id}/health", response_model=HostHealthResponse | None)
async def get_host_health(host_id: int, session: AsyncSession = Depends(get_async_session)) -> HostHealth | None:
    """Return the most recent health status for a host."""
    result = await session.execute(
        select(HostHealth)
        .where(HostHealth.host_id == host_id)
        .order_by(HostHealth.checked_at.desc())
        .limit(1)
    )
    row = result.scalars().first()
    return row


@router.get("/{host_id}/health/history", response_model=List[HostHealthResponse])
async def host_health_history(
    host_id: int,
    limit: int = 100,
    session: AsyncSession = Depends(get_async_session),
) -> List[HostHealth]:
    """Return recent health check history for a host."""
    result = await session.execute(
        select(HostHealth)
        .where(HostHealth.host_id == host_id)
        .order_by(HostHealth.checked_at.desc())
        .limit(limit)
    )
    rows = result.scalars().all()
    return rows


@router.get("/{host_id}/actions/history", response_model=List[ActionRunResponse])
async def host_actions_history(
    host_id: int,
    limit: int = 50,
    session: AsyncSession = Depends(get_async_session),
) -> List[ActionRun]:
    """Return recent action run history for a host."""
    result = await session.execute(
        select(ActionRun)
        .where(ActionRun.host_id == host_id)
        .order_by(ActionRun.started_at.desc())
        .limit(limit)
    )
    runs = result.scalars().all()
    return runs


@router.patch("/{host_id}/notify")
async def set_notify(host_id: int, enabled: bool, session: AsyncSession = Depends(get_async_session)) -> dict[str, bool]:
    """Enable or disable Telegram notifications for a host."""
    host = await session.get(Host, host_id)
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    host.notify_enabled = bool(enabled)
    await session.commit()
    return {"host_id": host_id, "notify_enabled": host.notify_enabled}
