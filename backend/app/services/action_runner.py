"""Action execution and recording service."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, Optional, List

from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models import ActionRun, ActionStatus, Host
from ..drivers import get_driver
from ..services.telegram import send_alert
from ..services.app_settings import get_telegram_severity
from ..services.severity import evaluate_severity

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


def parse_ussd_fields_from_message(msg: str) -> Dict[str, Any]:
    """
    Extrae datos_mb, validos_dias, saldo desde el texto del USSD.

    REGLAS IMPORTANTES:
    - DATOS: solo se extrae desde el label "Datos:" (ignora "toDus:", "toDus", "todus", etc.)
    - VALIDOS: soporta "validos 33 dias" y también "validos: 33 dias"
    - SALDO: intenta "Saldo: X" si existe

    Devuelve dict con ok_parse y campos extraídos.
    """
    out: Dict[str, Any] = {"ok_parse": False}

    if not msg:
        return out

    t = msg.lower()
    t = t.replace("días", "dias").replace("día", "dia")
    t = t.replace(",", ".")  # 1,5 -> 1.5
    t = t.replace("\n", " ")

    # -------------------------
    # DATOS (SOLO desde "Datos:")
    # Puede venir "Datos: 11.05 GB" o "Datos: 900 MB"
    # Si aparece más de una vez, tomamos la ÚLTIMA ocurrencia.
    # -------------------------
    datos_matches = re.findall(r"datos\s*:\s*(\d+(?:\.\d+)?)\s*(gb|mb)\b", t)
    if datos_matches:
        val_str, unit = datos_matches[-1]  # <-- la última ocurrencia de "Datos:"
        try:
            val = float(val_str)
            datos_mb = val * 1024.0 if unit == "gb" else val
            out["datos_mb"] = float(datos_mb)
        except Exception:
            pass

    # -------------------------
    # VALIDOS / VÁLIDOS
    # Soporta:
    # - "validos 33 dias"
    # - "validos: 33 dias"
    # - "validos=33 dias" (por si acaso)
    # -------------------------
    m = re.search(r"\bvalidos?\b\s*[:=\s]\s*(\d+)\s*dias?\b", t)
    if m:
        try:
            out["validos_dias"] = int(m.group(1))
        except Exception:
            pass

    # -------------------------
    # SALDO (opcional)
    # -------------------------
    m = re.search(r"\bsaldo\b\s*[:=\-]?\s*\$?\s*(\d+(?:\.\d+)?)\b", t)
    if m:
        try:
            out["saldo"] = float(m.group(1))
        except Exception:
            pass

    # ok_parse si logró algo útil
    if any(k in out for k in ("datos_mb", "validos_dias", "saldo")):
        out["ok_parse"] = True

    return out



def fmt_mb(mb: Any) -> str:
    try:
        mb = float(mb)
    except Exception:
        return "n/a"
    return f"{mb/1024:.2f} GB" if mb >= 1024 else f"{mb:.0f} MB"


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

            latest = extract_latest_ussd(response_raw)
            response_parsed = {"ussd_latest": latest}

            # Parsear campos desde el texto del último USSD (si existe)
            if latest and latest.get("message"):
                msg_txt = str(latest.get("message"))
                fields = parse_ussd_fields_from_message(msg_txt)
                response_parsed.update(fields)
                response_parsed["time"] = latest.get("time") or datetime.utcnow().isoformat()

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

        # 1) Enviar SIEMPRE el último USSD (si hay)
        if latest and latest.get("message"):
            msg = str(latest.get("message"))
            t = (
                (response_parsed.get("time") if isinstance(response_parsed, dict) else None)
                or latest.get("time")
                or datetime.utcnow().isoformat()
            )

            message = (
                "MoniTe – USSD (último)\n"
                f"Host: {host.name} ({host.ip})\n"
                f"Hora: {t}\n"
                f"{msg}"
            )
            await send_alert(host.id, "ussd_latest", message)

        # 2) Mantener alerta especial si hubo "saldo insuficiente"
        if ussd_raw_for_alerts is not None and has_saldo_insuficiente(ussd_raw_for_alerts):
            message = (
                "ALERTA MoniTe – Saldo insuficiente\n"
                f"Host: {host.name} ({host.ip})\n"
                f"Hora: {datetime.utcnow().isoformat()}Z"
            )
            await send_alert(host.id, "low_balance", message)

        # 3) Severidad configurable desde el front
        parsed = response_parsed if isinstance(response_parsed, dict) else None
        if parsed and parsed.get("ok_parse") is True:
            datos_mb = parsed.get("datos_mb")
            validos_dias = parsed.get("validos_dias")
            saldo = parsed.get("saldo")
            t = parsed.get("time") or datetime.utcnow().isoformat()

            thresholds = await get_telegram_severity(session)
            sev = evaluate_severity(datos_mb, validos_dias, thresholds)

            if sev:
                msg = (
                    f"{sev} – Estado del servicio\n"
                    f"Host: {host.name} ({host.ip})\n"
                    f"Lectura: {t}\n"
                    f"Datos: {fmt_mb(datos_mb)}\n"
                    f"Válidos: {validos_dias if validos_dias is not None else 'n/a'} días\n"
                    f"Saldo: {saldo if saldo is not None else 'n/a'}"
                )
                await send_alert(host.id, f"sev_{sev.lower()}", msg)

    # Falla (sin respuesta)
    if telegram_enabled and status == ActionStatus.FAIL.value and attempt >= max_attempts:
        message = (
            "ALERTA MoniTe – Router sin respuesta\n"
            f"Host: {host.name} ({host.ip})\n"
            f"Acción: {action_key}\n"
            f"Intentos: {attempt}\n"
            f"Error: {error_message}\n"
            f"Hora: {datetime.utcnow().isoformat()}Z"
        )
        await send_alert(host.id, "no_response", message)

    return run
