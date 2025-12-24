"""Action execution and recording service."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional, List

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import ActionRun, ActionStatus, Host
from ..drivers import get_driver
from ..services.telegram import send_alert

logger = logging.getLogger(__name__)


# ------------------------
# Helpers
# ------------------------

def _to_json_text(value: Any) -> Optional[str]:
    """Serialize values safely for SQLite TEXT columns."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        return str(value)


def _parse_mikrotik_time(s: str) -> Optional[datetime]:
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def _ensure_mikrotik_logs(raw: Any) -> List[Dict[str, Any]]:
    """
    Normaliza logs MikroTik desde:
      - raw str (JSON)
      - raw list[dict]
    a list[dict]
    """
    if raw is None:
        return []

    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return []

    if isinstance(raw, list):
        return [x for x in raw if isinstance(x, dict)]

    return []


def extract_latest_ussd(raw: Any) -> Optional[Dict[str, Any]]:
    """
    Devuelve SOLO el USSD más nuevo (por timestamp) desde raw (str o list).
    """
    logs = _ensure_mikrotik_logs(raw)

    latest: Optional[Dict[str, Any]] = None
    latest_time: Optional[datetime] = None

    for item in logs:
        msg = str(item.get("message", "")).strip()
        if not msg.startswith("USSD:"):
            continue

        t = _parse_mikrotik_time(str(item.get("time", ""))) or datetime.min

        if latest is None or t > (latest_time or datetime.min):
            latest = item
            latest_time = t

    if not latest:
        return None

    return {"time": latest.get("time"), "message": latest.get("message")}


def has_saldo_insuficiente(raw: Any) -> bool:
    """
    True si en CUALQUIER USSD del batch aparece "saldo insuficiente".
    """
    logs = _ensure_mikrotik_logs(raw)
    for item in logs:
        msg = str(item.get("message", "")).strip()
        if msg.startswith("USSD:") and "saldo insuficiente" in msg.lower():
            return True
    return False


# ------------------------
# Main logic
# ------------------------

async def execute_and_record(
    session: AsyncSession,
    host: Host,
    action_key: str,
    *,
    attempt: int = 1,
    max_attempts: int = 1,
    telegram_enabled: bool = True,
    **params: Any,
) -> ActionRun:
    driver = get_driver(host.router_type)

    start_time = datetime.utcnow()

    status = ActionStatus.SUCCESS.value
    stdout: Optional[Any] = None
    stderr: Optional[Any] = None
    response_raw: Optional[Any] = None
    response_parsed: Optional[Any] = None
    error_message: Optional[str] = None

    # Para alertas USSD (en memoria, raw puede ser str o list)
    ussd_raw_for_alerts: Optional[Any] = None

    try:
        result: Dict[str, Any] = await driver.execute_action(host, action_key, **params)
        response_raw = result.get("raw")

        if action_key == "VER_LOGS_USSD":
            # Guardamos raw en memoria solo para alertas
            ussd_raw_for_alerts = response_raw

            # Guardamos en parsed solo lo útil para UI
            response_parsed = {"ussd_latest": extract_latest_ussd(response_raw)}

            # No guardamos stdout ni response_raw gigantes
            stdout = None
            response_raw = None
        else:
            response_parsed = result.get("parsed")
            stdout = response_raw

    except Exception as exc:
        status = ActionStatus.FAIL.value
        error_message = str(exc)
        stderr = str(exc)
        logger.error("Action %s on host %s failed: %s", action_key, host.id, exc)

    finish_time = datetime.utcnow()
    duration_ms = (finish_time - start_time).total_seconds() * 1000.0

    # ------------------------
    # Persist
    # ------------------------
    run = ActionRun(
        host_id=host.id,
        router_type=host.router_type,
        action_key=action_key,
        started_at=start_time,
        finished_at=finish_time,
        duration_ms=duration_ms,
        status=status,
        stdout=_to_json_text(stdout),
        stderr=_to_json_text(stderr),
        response_parsed=_to_json_text(response_parsed),
        response_raw=None,  # ⛔ nunca guardamos logs gigantes
        error_message=error_message,
    )

    session.add(run)
    await session.commit()
    await session.refresh(run)

    # ------------------------
    # Alerts
    # ------------------------
    if telegram_enabled and status == ActionStatus.SUCCESS.value and action_key == "VER_LOGS_USSD":
        latest = None
        if isinstance(response_parsed, dict):
            latest = response_parsed.get("ussd_latest")

        # ✅ Mandar SIEMPRE el último USSD (Saldo/Tarifa/etc.)
        if latest and latest.get("message"):
            msg = str(latest.get("message"))
            t = latest.get("time") or datetime.utcnow().isoformat()

            message = (
                f"MoniTe – USSD (último)\n"
                f"Host: {host.name} ({host.ip})\n"
                f"Hora: {t}\n"
                f"{msg}"
            )
            await send_alert(host.id, "ussd_latest", message)

        # ✅ Mantener alerta especial si hubo "saldo insuficiente" en cualquier parte
        if ussd_raw_for_alerts is not None and has_saldo_insuficiente(ussd_raw_for_alerts):
            message = (
                f"ALERTA MoniTe – Saldo insuficiente\n"
                f"Host: {host.name} ({host.ip})\n"
                f"Hora: {datetime.utcnow()}"
            )
            await send_alert(host.id, "low_balance", message)

    if telegram_enabled and status == ActionStatus.FAIL.value and attempt >= max_attempts:
        message = (
            f"ALERTA MoniTe – Router sin respuesta\n"
            f"Host: {host.name} ({host.ip})\n"
            f"Acción: {action_key}\n"
            f"Intentos: {attempt}\n"
            f"Error: {error_message}\n"
            f"Hora: {datetime.utcnow()}"
        )
        await send_alert(host.id, "no_response", message)

    return run
