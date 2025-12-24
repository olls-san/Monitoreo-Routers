"""Health monitoring and alerting service.

This module provides functions to perform connectivity checks on hosts,
persist the results to the database and send notifications when a host
changes state. It also includes a function to generate and send a daily
summary of host statuses and recent alerts.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_async_session
from ..models import Host, HostHealth, ActionRun, ActionStatus
from ..drivers import get_driver
from ..services.telegram import send_alert

logger = logging.getLogger(__name__)


async def check_host(session: AsyncSession, host: Host) -> HostHealth:
    """Check the connectivity of a single host and persist the result.

    The host's `validate()` method on its driver is used to determine
    connectivity. If the driver validation raises an exception, the host
    is considered offline. Latency in milliseconds is measured for
    successful checks. The host's cached status fields are updated.

    Args:
        session: SQLAlchemy async session.
        host: Host entity to check.

    Returns:
        The persisted HostHealth instance.
    """
    driver = get_driver(host.router_type)

    previous_status: Optional[str] = host.last_status
    status: str = "offline"
    latency_ms: Optional[float] = None
    error_message: Optional[str] = None
    start = time.perf_counter()
    try:
        # Use driver.validate() as a lightweight health check
        await driver.validate(host)
        elapsed = (time.perf_counter() - start) * 1000.0
        latency_ms = elapsed
        status = "online"
    except Exception as exc:
        status = "offline"
        error_message = str(exc)
        logger.debug("Health check for host %s failed: %s", host.id, exc)

    now = datetime.utcnow()

    # Persist health history row
    health = HostHealth(
        host_id=host.id,
        status=status,
        latency_ms=latency_ms,
        error_message=error_message,
        checked_at=now,
    )
    session.add(health)

    # Update host cache fields
    host.last_status = status
    host.last_checked_at = now
    host.last_latency_ms = latency_ms

    # Send Telegram alert if state changed
    if host.notify_enabled and previous_status and previous_status != status:
        try:
            if status == "offline":
                msg = (
                    f"🔴 Host offline\n"
                    f"Host: {host.name} ({host.ip})\n"
                    f"Antes: {previous_status} -> Ahora: {status}\n"
                    f"Hora: {now.isoformat()}Z\n"
                    f"Error: {error_message or 'n/a'}"
                )
                await send_alert(host.id, "host_offline", msg)
            else:
                lat = f"{latency_ms:.0f} ms" if latency_ms is not None else "n/a"
                msg = (
                    f"🟢 Host online\n"
                    f"Host: {host.name} ({host.ip})\n"
                    f"Antes: {previous_status} -> Ahora: {status}\n"
                    f"Hora: {now.isoformat()}Z\n"
                    f"Latencia: {lat}"
                )
                await send_alert(host.id, "host_online", msg)
        except Exception as exc:
            logger.error("Failed to send state change alert for host %s: %s", host.id, exc)

    # Flush changes but let caller decide commit/rollback
    await session.flush()
    return health


async def check_all_hosts(session: AsyncSession) -> List[HostHealth]:
    """Check all hosts and return a list of health entries."""
    result = await session.execute(select(Host))
    hosts = result.scalars().all()
    checks: List[HostHealth] = []
    for host in hosts:
        checks.append(await check_host(session, host))
    return checks


async def send_daily_summary(session: AsyncSession) -> None:
    """Compute and send a daily summary of host statuses and recent events.

    The summary includes:
        - Total number of hosts.
        - Number of currently offline hosts (based on cached status).
        - Count of offline events in the last 24 hours.
        - Count of action failures in the last 24 hours.
        - Top 5 hosts with the most offline events in the last 24 hours.

    The summary is sent via Telegram using the send_alert helper. If
    Telegram is not configured or sending fails, the exception is
    suppressed and logged.
    """
    now = datetime.utcnow()
    since = now - timedelta(hours=24)

    # Total hosts
    total_hosts = (await session.execute(select(func.count()).select_from(Host))).scalar_one()
    # Offline currently
    offline_now = (await session.execute(select(func.count()).select_from(Host).where(Host.last_status == "offline"))).scalar_one()
    # Offline events last 24h
    offline_events_24h = (
        await session.execute(
            select(func.count())
            .select_from(HostHealth)
            .where(and_(HostHealth.checked_at >= since, HostHealth.status == "offline"))
        )
    ).scalar_one()
    # Action failures last 24h
    action_errors_24h = (
        await session.execute(
            select(func.count())
            .select_from(ActionRun)
            .where(and_(ActionRun.started_at >= since, ActionRun.status == ActionStatus.FAIL.value))
        )
    ).scalar_one()
    # Top 5 hosts by offline events last 24h
    result = await session.execute(
        select(Host.name, Host.ip, func.count().label("cnt"))
        .join(HostHealth, HostHealth.host_id == Host.id)
        .where(and_(HostHealth.checked_at >= since, HostHealth.status == "offline"))
        .group_by(Host.id)
        .order_by(desc("cnt"))
        .limit(5)
    )
    top_offline = result.all()

    lines: List[str] = []
    lines.append("📊 Resumen diario MoniTe")
    lines.append(f"UTC: {now.isoformat()}Z")
    lines.append("")
    lines.append(f"Hosts totales: {total_hosts}")
    lines.append(f"Hosts offline ahora: {offline_now}")
    lines.append(f"Eventos offline (24h): {offline_events_24h}")
    lines.append(f"Acciones fallidas (24h): {action_errors_24h}")
    if top_offline:
        lines.append("")
        lines.append("Top inestables (24h):")
        for name, ip, cnt in top_offline:
            lines.append(f"• {name} ({ip}) — {cnt} caídas")

    message = "\n".join(lines)

    # Use a generic alert key for summaries so cooldown is per host
    try:
        # We pass host_id=0 to indicate a global alert
        await send_alert(0, "daily_summary", message)
    except Exception as exc:
        logger.error("Failed to send daily summary: %s", exc)