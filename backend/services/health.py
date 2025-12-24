"""Health check utilities for hosts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..drivers.base import get_driver
from ..models import Host
from ..schemas import HealthResponse


async def check_host_health(session: AsyncSession, host: Host) -> HealthResponse:
    """Perform a health check on a single host and update its status safely.

    The driver may return either a dict with keys ``online``, ``latency_ms`` and
    ``error``, or a tuple ``(latency_ms, error)``.  This helper normalises
    both forms into a consistent (online, latency, error) triple.  If the
    driver is not registered or raises any exception, the host is marked
    offline and the error message is propagated.
    """
    checked_at = datetime.now(timezone.utc)
    online: bool = False
    latency: float | None = None  # type: ignore[assignment]
    error: str | None = None  # type: ignore[assignment]

    try:
        driver = get_driver(host)
        result = await driver.health_check()
        # Normalise return type
        if isinstance(result, dict):
            online = bool(result.get("online", False))
            latency = result.get("latency_ms", None)
            error = result.get("error", None)
        elif isinstance(result, (tuple, list)) and len(result) == 2:
            # Tuple form: (latency_ms, error)
            latency, error = result
            online = error is None
        else:
            # Unexpected result type
            online = False
            latency = None
            error = f"Invalid health_check() return type: {type(result).__name__}"
    except Exception as exc:
        online = False
        latency = None
        error = str(exc)

    # Update host last known state
    host.last_online = online
    host.last_latency_ms = latency
    host.last_check_at = checked_at
    await session.flush()  # ensure changes are tracked

    return HealthResponse(
        host_id=host.id,
        online=online,
        latency_ms=latency,
        checked_at=checked_at,
        error=error,
    )


async def check_all_hosts(session: AsyncSession) -> List[HealthResponse]:
    """Check the health of all hosts in the database and return a list of responses."""
    result = await session.execute(select(Host))
    hosts = result.scalars().all()
    health_reports = []
    for host in hosts:
        report = await check_host_health(session, host)
        health_reports.append(report)
    return health_reports