"""Telegram alerting utilities for MoniTe Web."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Tuple

import httpx

from ..models import Host
from ..settings import settings

# In-memory store tracking the last time an alert was sent for a given
# (host_id, alert_type) pair. This prevents spamming the same notification
# multiple times within a cooldown window.
_last_alert_sent: Dict[Tuple[int, str], datetime] = {}


async def send_alert(host: Host, alert_type: str, message: str) -> None:
    """Send a Telegram message respecting cooldown rules.

    If either the Telegram token or chat ID is unset, this function does
    nothing. Alerts are rate limited based on `settings.telegram_cooldown_seconds`.
    """
    token = settings.telegram_token
    chat_id = settings.telegram_chat_id
    if not token or not chat_id:
        return

    key = (host.id, alert_type)
    now = datetime.now(timezone.utc)
    last_time = _last_alert_sent.get(key)
    if last_time and (now - last_time).total_seconds() < settings.telegram_cooldown_seconds:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}
    async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
        try:
            await client.post(url, json=payload)
        finally:
            _last_alert_sent[key] = now