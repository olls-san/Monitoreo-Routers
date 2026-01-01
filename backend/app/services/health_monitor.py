"""Health monitoring and alerting service.

This module provides functions to perform connectivity checks on hosts,
persist the results to the database and send notifications when a host
changes state. It also includes a function to generate and send a daily
summary of host statuses and recent alerts.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from typing import Any, List, Optional, Tuple

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..drivers import get_driver
from ..models import Host, HostHealth, ActionRun, ActionStatus
from ..services.telegram import send_alert
from ..services.app_settings import get_telegram_severity
from ..services.severity import evaluate_severity

logger = logging.getLogger(__name__)


# ------------------------
# Helpers (formato)
# ------------------------

def fmt_mb(mb: Any) -> str:
    try:
        mb = float(mb)
    except Exception:
        return "n/a"
    if mb >= 1024:
        return f"{mb/1024:.2f} GB"
    return f"{mb:.0f} MB"


def fmt_dt_short(iso_or_dt: Any) -> str:
    try:
        if isinstance(iso_or_dt, datetime):
            dt = iso_or_dt
        else:
            dt = datetime.fromisoformat(str(iso_or_dt).replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(iso_or_dt)


def host_line(name: str, ip: str, datos_mb: Any, validos_dias: Any, saldo: Any) -> str:
    vd = validos_dias if validos_dias is not None else "n/a"
    sa = saldo if saldo is not None else "n/a"
    return f"• {name} ({ip}) — Datos: {fmt_mb(datos_mb)} | Vigencia: {vd}d | Saldo: {sa}"


# ------------------------
# DB helpers
# ------------------------

async def get_latest_ussd_parsed_map(session: AsyncSession, host_ids: List[int]) -> dict:
    """
    Devuelve {host_id: parsed_dict} con el último VER_LOGS_USSD SUCCESS por host.
    parsed_dict viene de ActionRun.response_parsed (json text).
    """
    if not host_ids:
        return {}

    stmt = (
        select(ActionRun.host_id, ActionRun.response_parsed, ActionRun.started_at)
        .where(ActionRun.host_id.in_(host_ids))
        .where(ActionRun.action_key == "VER_LOGS_USSD")
        .where(ActionRun.status == ActionStatus.SUCCESS.value)
        .order_by(ActionRun.host_id, desc(ActionRun.started_at))
    )

    rows = (await session.execute(stmt)).all()

    out = {}
    for host_id, resp_txt, _started_at in rows:
        if host_id in out:
            continue
        if not resp_txt:
            continue
        try:
            d = json.loads(resp_txt) if isinstance(resp_txt, str) else resp_txt
            if isinstance(d, dict):
                out[host_id] = d
        except Exception:
            continue
    return out


async def last_n_statuses(session: AsyncSession, host_id: int, n: int = 6) -> List[str]:
    """
    Devuelve los últimos N estados (más recientes primero) desde HostHealth.
    """
    rows = await session.execute(
        select(HostHealth.status)
        .where(HostHealth.host_id == host_id)
        .order_by(HostHealth.checked_at.desc())
        .limit(n)
    )
    return [r[0] for r in rows.all()]


def should_alert_offline_confirmed(last_statuses: List[str], required: int = 5) -> bool:
    """
    Regla anti-spam:
    - Alertar SOLO cuando se cumple por primera vez "required OFFLINE seguidos".
    - Es decir: los últimos 'required' son offline,
      y el siguiente (required+1) NO es offline (o no existe).
    last_statuses debe venir en orden: más reciente primero.
    """
    if len(last_statuses) < required:
        return False

    # últimos required (más recientes)
    head = last_statuses[:required]
    if not all(s == "offline" for s in head):
        return False

    # borde: evitar repetir si ya llevaba offline antes del grupo
    if len(last_statuses) >= required + 1:
        return last_statuses[required] != "offline"

    return True


# ------------------------
# Checks
# ------------------------

async def check_host(session: AsyncSession, host: Host) -> HostHealth:
    """Check the connectivity of a single host and persist the result."""
    driver = get_driver(host.router_type)

    previous_status: Optional[str] = host.last_status
    status: str = "offline"
    latency_ms: Optional[float] = None
    error_message: Optional[str] = None

    start = time.perf_counter()
    try:
        await driver.validate(host)
        elapsed = (time.perf_counter() - start) * 1000.0
        latency_ms = elapsed
        status = "online"
    except Exception as exc:
        status = "offline"
        error_message = str(exc)
        logger.debug("Health check for host %s failed: %s", host.id, exc)

    now = datetime.utcnow()

    # Persist health row
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

    # Importante: flush para que el health recién creado se vea en queries del mismo ciclo
    await session.flush()

    # ------------------------
    # Telegram alerts (anti-spam OFFLINE + formato estructurado)
    # ------------------------
    if host.notify_enabled:
        try:
            if status == "online":
                # ONLINE: avisar solo cuando RECUPERA (evita ruido)
                # (Si quieres avisar siempre que esté online, cambia la condición)
                if previous_status and previous_status != "online":
                    lat = f"{latency_ms:.0f} ms" if latency_ms is not None else "n/a"
                    msg = (
                        "🟢 ONLINE — Host recuperado\n"
                        "━━━━━━━━━━━━━━━━━━━━\n"
                        f"📍 Host: {host.name}\n"
                        f"🌐 IP: {host.ip}\n"
                        f"🕒 Hora: {now.isoformat()}Z\n\n"
                        f"📶 Latencia: {lat}\n\n"
                        "Acción sugerida:\n"
                        "• Confirmar estabilidad en el panel\n"
                        "• Ejecutar una acción (si aplica)"
                    )
                    await send_alert(host.id, "host_online", msg)

            else:
                # OFFLINE: anti-spam → alertar solo cuando se cumple 5 OFFLINE seguidos (primera vez)
                last6 = await last_n_statuses(session, host.id, 6)
                if should_alert_offline_confirmed(last6, required=5):
                    msg = (
                        "🔴 OFFLINE — Confirmado (5 chequeos)\n"
                        "━━━━━━━━━━━━━━━━━━━━\n"
                        f"📍 Host: {host.name}\n"
                        f"🌐 IP: {host.ip}\n"
                        f"🕒 Hora: {now.isoformat()}Z\n\n"
                        "Criterio:\n"
                        "• OFFLINE en 5 chequeos consecutivos\n\n"
                        "Acción sugerida:\n"
                        "• Revisar conectividad / VPN / energía\n"
                        "• Verificar que el router esté encendido\n"
                        "• Intentar un chequeo manual"
                    )
                    await send_alert(host.id, "host_offline_confirmed", msg)

        except Exception as exc:
            logger.error("Failed to send health alert for host %s: %s", host.id, exc)

    return health


async def check_all_hosts(session: AsyncSession) -> List[HostHealth]:
    """Check all hosts and return a list of health entries."""
    result = await session.execute(select(Host))
    hosts = result.scalars().all()
    checks: List[HostHealth] = []
    for host in hosts:
        checks.append(await check_host(session, host))
    return checks


# ------------------------
# Daily summary
# ------------------------

async def send_daily_summary(session: AsyncSession) -> None:
    now = datetime.utcnow()

    # Umbrales desde el FRONT (DB)
    thresholds = await get_telegram_severity(session)

    # --------------------
    # 1) Estado actual
    # --------------------
    total_hosts = (await session.execute(select(func.count()).select_from(Host))).scalar_one()

    offline_rows = await session.execute(
        select(Host.id, Host.name, Host.ip)
        .where(Host.last_status == "offline")
        .order_by(Host.name.asc())
    )
    offline_hosts = offline_rows.all()
    offline_now = len(offline_hosts)
    online_now = max(total_hosts - offline_now, 0)

    # --------------------
    # 2) Último VER_LOGS_USSD por host (para severidad)
    # --------------------
    host_rows = await session.execute(select(Host.id, Host.name, Host.ip).order_by(Host.name.asc()))
    hosts: List[Tuple[int, str, str]] = host_rows.all()

    host_ids = [hid for (hid, _n, _ip) in hosts]
    latest_parsed_by_host = await get_latest_ussd_parsed_map(session, host_ids)

    crit_lines: List[str] = []
    high_lines: List[str] = []
    med_lines: List[str] = []

    per_host_alerts: List[Tuple[int, str, str, str]] = []  # (host_id, sev, name, ip)

    for host_id, name, ip in hosts:
        parsed = latest_parsed_by_host.get(host_id)
        if not isinstance(parsed, dict) or parsed.get("ok_parse") is not True:
            continue

        datos_mb = parsed.get("datos_mb")
        validos_dias = parsed.get("validos_dias")
        saldo = parsed.get("saldo")

        sev = evaluate_severity(datos_mb, validos_dias, thresholds)
        if not sev:
            continue

        line = host_line(name, ip, datos_mb, validos_dias, saldo)

        if sev == "CRÍTICO":
            crit_lines.append(line)
        elif sev == "ALTA":
            high_lines.append(line)
        elif sev == "MEDIA":
            med_lines.append(line)

        per_host_alerts.append((host_id, sev, name, ip))

    # --------------------
    # 3) Mensaje global (1 solo)
    # --------------------
    lines: List[str] = []
    lines.append("📌 MoniTe — Resumen diario")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"🕒 {fmt_dt_short(now)} (UTC)")
    lines.append("")

    lines.append("A) Estado actual")
    lines.append(f"• Hosts totales: {total_hosts}")
    lines.append(f"• Online: {online_now}")
    lines.append(f"• Offline: {offline_now}")

    if offline_hosts:
        lines.append("• Offline (lista):")
        for _hid, n, ip in offline_hosts:
            lines.append(f"  • {n} ({ip})")
    else:
        lines.append("• Offline (lista): ✅ OK")

    lines.append("")
    lines.append("B) Preventivas (por severidad)")

    def block(title: str, arr: List[str]) -> None:
        if not arr:
            lines.append(f"{title}: ✅ OK")
        else:
            lines.append(f"{title}:")
            lines.extend(arr)

    block("🚨 CRÍTICOS", crit_lines)
    block("⚠️ ALTAS", high_lines)
    block("🟡 MEDIAS", med_lines)

    lines.append("")
    lines.append("—")
    lines.append("⚙️ Fuente: último USSD por host")

    header = "\n".join(lines)
    await send_alert(0, "daily_summary", header)

    # --------------------
    # 4) Mensaje por host OFFLINE (del resumen diario)
    # --------------------
    for host_id, name, ip in offline_hosts:
        msg = (
            "🔴 OFFLINE — Host sin respuesta\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"📍 Host: {name}\n"
            f"🌐 IP: {ip}\n"
            f"🕒 UTC: {now.isoformat()}Z\n\n"
            "Acción sugerida:\n"
            "• Revisar conectividad / VPN / energía\n"
            "• Intentar validar desde el panel"
        )
        await send_alert(host_id, "daily_offline", msg)

    # --------------------
    # 5) Un mensaje por host con severidad (CRÍTICO/ALTA/MEDIA)
    # --------------------
    for host_id, sev, name, ip in per_host_alerts:
        parsed = latest_parsed_by_host.get(host_id) or {}
        t = parsed.get("time") or now.isoformat()
        datos_mb = parsed.get("datos_mb")
        validos_dias = parsed.get("validos_dias")
        saldo = parsed.get("saldo")

        icon = {"CRÍTICO": "🚨", "ALTA": "⚠️", "MEDIA": "🟡"}.get(sev, "ℹ️")
        title = {
            "CRÍTICO": "CRÍTICO — Atención inmediata",
            "ALTA": "ALTA — Atención requerida",
            "MEDIA": "MEDIA — Preventiva",
        }.get(sev, f"{sev} — Estado")

        msg = (
            f"{icon} {title}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"📍 Host: {name}\n"
            f"🌐 IP: {ip}\n"
            f"🕒 Lectura: {t}\n\n"
            "📊 Estado\n"
            f"• Datos: {fmt_mb(datos_mb)}\n"
            f"• Vigencia: {validos_dias if validos_dias is not None else 'n/a'} días\n"
            f"• Saldo: {saldo if saldo is not None else 'n/a'}\n\n"
            "⚙️ Origen: USSD"
        )

        await send_alert(host_id, f"daily_sev_{sev.lower()}", msg)
