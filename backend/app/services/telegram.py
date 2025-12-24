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

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Tuple

import httpx

from ..config import settings

logger = logging.getLogger(__name__)


# Keep track of last alert send times to implement cooldown. Key is
# (host_id, alert_key). Value is datetime of last send.
_LAST_ALERT_TIMES: Dict[Tuple[int, str], datetime] = {}

# Cooldown period in seconds for duplicate alerts. This value comes
# from the application settings and can be configured via environment
# variables. Defaults to 900 seconds (15 minutes) if not set.
def _cooldown_seconds() -> int:
    try:
        return int(getattr(settings, "telegram_cooldown_seconds", 900) or 900)
    except Exception:
        return 900


async def _post_message(text: str) -> None:
    """Send a message to Telegram via HTTP API.

    This helper uses httpx to issue a POST request to the
    `/sendMessage` endpoint. It does not retry on failure; the
    calling code should catch exceptions.
    """
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
    """Send an alert message with anti-spam control.

    Args:
        host_id: ID of the host that triggered the alert.
        alert_key: A stable identifier for the alert type
            (e.g. "low_data", "expiring_data", "low_balance", "no_response").
        message: The text to send to Telegram.

    The function checks whether a message of this type has been sent
    recently for the same host and suppresses duplicates within the
    cooldown period. This prevents flooding chats with repeated
    alerts when an issue persists.
    """
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
