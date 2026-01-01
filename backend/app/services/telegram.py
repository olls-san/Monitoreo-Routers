"""Telegram alerting service.

This module wraps the Telegram Bot API to send messages to a
configured chat. It also implements a simple anti-spam cooldown
mechanism so that alerts of the same type for the same host are
not sent too frequently.

If the token or chat ID are not configured (via environment
variables ``MONITE_TELEGRAM_TOKEN`` and ``MONITE_TELEGRAM_CHAT_ID``),
calls to :func:`send_alert` will be silently ignored.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import httpx

from ..config import settings

logger = logging.getLogger(__name__)


# Keep track of last alert send times to implement cooldown. Key is
# (host_id, alert_key). Value is datetime of last send.
_LAST_ALERT_TIMES: Dict[Tuple[int, str], datetime] = {}


def _cooldown_seconds() -> int:
    try:
        return int(getattr(settings, "telegram_cooldown_seconds", 900) or 900)
    except Exception:
        return 900


def _safe_str(x: object) -> str:
    try:
        s = str(x)
    except Exception:
        return "n/a"
    return s


def format_msg(
    *,
    title: str,
    host_name: Optional[str] = None,
    host_ip: Optional[str] = None,
    when: Optional[str] = None,
    sections: Optional[List[Tuple[str, List[str]]]] = None,
    suggested: Optional[List[str]] = None,
    footer: Optional[str] = None,
) -> str:
    """
    Formato unificado para Telegram (mismo estilo que resumen/chequeos).

    sections: lista de tuples (titulo_seccion, lineas)
      ejemplo: [("📊 Estado", ["• Datos: 5.2 GB", "• Vigencia: 3 días"])]
    suggested: lista de bullets para "Acción sugerida"
    """
    lines: List[str] = []
    lines.append(title)
    lines.append("━━━━━━━━━━━━━━━━━━━━")

    if host_name or host_ip:
        hn = host_name or "n/a"
        hip = host_ip or "n/a"
        lines.append(f"📍 Host: {hn}")
        lines.append(f"🌐 IP: {hip}")

    if when:
        lines.append(f"🕒 Hora: {when}")

    if sections:
        for sec_title, sec_lines in sections:
            if not sec_lines:
                continue
            lines.append("")
            lines.append(sec_title)
            lines.extend(sec_lines)

    if suggested:
        lines.append("")
        lines.append("Acción sugerida:")
        for s in suggested:
            lines.append(f"• {s}")

    if footer:
        lines.append("")
        lines.append(footer)

    return "\n".join(lines)


async def _post_message(text: str) -> None:
    """Send a message to Telegram via HTTP API."""
    if not settings.telegram_token or not settings.telegram_chat_id:
        logger.info("Telegram not configured; skipping message: %s", text)
        return
    token = settings.telegram_token
    chat_id = settings.telegram_chat_id
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()


async def send_alert(host_id: int, alert_key: str, message: str) -> None:
    """Send an alert message with anti-spam control."""
    now = datetime.utcnow()
    key = (host_id, alert_key)
    last_sent = _LAST_ALERT_TIMES.get(key)
    cooldown = timedelta(seconds=_cooldown_seconds())
    if last_sent and now - last_sent < cooldown:
        logger.debug(
            "Skipping alert %s for host %s due to cooldown (%ss)",
            alert_key,
            host_id,
            _cooldown_seconds(),
        )
        return
    try:
        await _post_message(message)
        _LAST_ALERT_TIMES[key] = now
        logger.info("Telegram alert sent for host %s (%s)", host_id, alert_key)
    except Exception as exc:
        logger.error("Failed to send Telegram message: %s", exc)
