"""API endpoints for retrieving read‑only global configuration.

This router exposes a minimal configuration payload that is safe for the
frontend to consume.  Only human‑readable values are returned; secrets
such as database credentials or API tokens are never included.  The
existing backend configuration (``backend/settings.py``) defined a
similar endpoint.  To unify the project under ``backend/app`` we
reimplement that behaviour here using the new settings model.
"""

from __future__ import annotations

from fastapi import APIRouter

from ..config import settings


router = APIRouter(prefix="/config", tags=["config"])


@router.get("/", response_model=dict)
async def get_config() -> dict[str, object]:
    """Return global settings relevant for the frontend.

    The response includes only non‑sensitive configuration values.  The
    scheduler timezone, a generic request timeout and whether Telegram
    notifications are configured are provided.  If additional values are
    required by the frontend in the future they should be added here
    explicitly to avoid leaking secrets.
    """
    return {
        # Use the scheduler timezone from the new settings.  Defaults to UTC.
        "scheduler_timezone": settings.scheduler_timezone,
        # Preserve the legacy behaviour of returning a request timeout
        # value.  The ``backend/app`` settings do not define
        # ``request_timeout``, so we hardcode a sensible default (10 seconds).
        "request_timeout": 10.0,
        # Expose whether Telegram is configured by checking that both
        # token and chat ID are present.  Booleans are safe to expose.
        "telegram_configured": bool(settings.telegram_token and settings.telegram_chat_id),
    }
