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
import json
from ..config import settings

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
    now = datetime.utcnow()

    # --------------------
    # A) Estado actual
    # --------------------
    total_hosts = (await session.execute(select(func.count()).select_from(Host))).scalar_one()

    offline_rows = await session.execute(
        select(Host.name)
        .where(Host.last_status == "offline")
        .order_by(Host.name.asc())
        .limit(8)
    )
    offline_names = [r[0] for r in offline_rows.all()]
    offline_now = len(offline_names)
    online_now = max(total_hosts - offline_now, 0)

    # --------------------
    # B) Preventivas (desde DB)
    # Tomamos la última ejecución exitosa de CONSULTAR_SALDO por host.
    # --------------------
    saldo_rows = await session.execute(
        select(ActionRun.host_id, Host.name, Host.ip, ActionRun.response_parsed, ActionRun.started_at)
        .join(Host, Host.id == ActionRun.host_id)
        .where(
            and_(
                ActionRun.action_key == "VER_LOGS_USSD",
                ActionRun.status == ActionStatus.SUCCESS.value,
            )
        )
        .order_by(desc(ActionRun.started_at))
        .limit(2000)
    )

    latest_by_host = {}
    for host_id, name, ip, resp, started_at in saldo_rows.all():
        if host_id in latest_by_host:
            continue

        # response_parsed puede venir como dict (si SQLAlchemy lo materializa)
        # o como string (si fue guardado como JSON string)
        parsed = None
        if isinstance(resp, dict):
            parsed = resp
        elif isinstance(resp, str) and resp.strip():
            try:
                parsed = json.loads(resp)
            except Exception:
                parsed = None

        if isinstance(parsed, dict):
            latest_by_host[host_id] = {
                "name": name,
                "ip": ip,
                "started_at": started_at,
                "parsed": parsed,
            }

    low_data_mb = int(getattr(settings, "telegram_low_data_mb", 1024) or 1024)
    exp_days = int(getattr(settings, "telegram_expiring_days", 3) or 3)
    low_balance = getattr(settings, "telegram_low_balance", None)

    def fmt_mb(mb):
        try:
            mb = float(mb)
        except Exception:
            return "n/a"
        if mb >= 1024:
            return f"{mb/1024:.2f} GB"
        return f"{mb:.0f} MB"

    low_data_list = []
    expiring_list = []
    low_balance_list = []

    for item in latest_by_host.values():
        p = item["parsed"]
        if p.get("ok_parse") is not True:
            continue

        datos_mb = p.get("datos_mb")
        validos_dias = p.get("validos_dias")
        saldo = p.get("saldo")

        if isinstance(datos_mb, (int, float)) and datos_mb < low_data_mb:
            low_data_list.append((item["name"], datos_mb, validos_dias))

        if isinstance(validos_dias, int) and validos_dias <= exp_days:
            expiring_list.append((item["name"], validos_dias, datos_mb))

        if low_balance is not None and isinstance(saldo, (int, float)) and saldo <= float(low_balance):
            low_balance_list.append((item["name"], saldo, datos_mb, validos_dias))

    # Orden por urgencia
    low_data_list.sort(key=lambda x: x[1])
    expiring_list.sort(key=lambda x: x[1])
    low_balance_list.sort(key=lambda x: x[1])

    # --------------------
    # Mensaje final
    # --------------------
    lines: List[str] = []
    lines.append("Resumen diario MoniTe")
    lines.append(f"UTC: {now.isoformat()}Z")
    lines.append("")
    lines.append("A) Estado actual")
    lines.append(f"- Hosts totales: {total_hosts}")
    lines.append(f"- Online: {online_now}")
    lines.append(f"- Offline: {offline_now}")
    if offline_names:
        lines.append("- Offline (lista corta):")
        for n in offline_names:
            lines.append(f"  • {n}")
    lines.append("")

    lines.append("B) Preventivas")
    if low_data_list:
        lines.append(f"- Datos < {fmt_mb(low_data_mb)}:")
        for name, mb, dias in low_data_list[:10]:
            lines.append(f"  • {name}: {fmt_mb(mb)} | válidos: {dias if dias is not None else 'n/a'} días")
        if len(low_data_list) > 10:
            lines.append(f"  +{len(low_data_list) - 10} más")
    else:
        lines.append(f"- Datos < {fmt_mb(low_data_mb)}: OK")

    if expiring_list:
        lines.append(f"- Vigencia ≤ {exp_days} días:")
        for name, dias, mb in expiring_list[:10]:
            lines.append(f"  • {name}: {dias} días | datos: {fmt_mb(mb)}")
        if len(expiring_list) > 10:
            lines.append(f"  +{len(expiring_list) - 10} más")
    else:
        lines.append(f"- Vigencia ≤ {exp_days} días: OK")

    if low_balance is None:
        lines.append("- Saldo bajo: desactivado")
    else:
        if low_balance_list:
            lines.append(f"- Saldo ≤ {low_balance}:")
            for name, s, mb, dias in low_balance_list[:10]:
                lines.append(f"  • {name}: {s} | datos: {fmt_mb(mb)} | válidos: {dias if dias is not None else 'n/a'} días")
            if len(low_balance_list) > 10:
                lines.append(f"  +{len(low_balance_list) - 10} más")
        else:
            lines.append(f"- Saldo ≤ {low_balance}: OK")

    message = "\n".join(lines)

    try:
        await send_alert(0, "daily_summary", message)
    except Exception as exc:
        logger.error("Failed to send daily summary: %s", exc)
