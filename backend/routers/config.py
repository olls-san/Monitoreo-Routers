"""API endpoints for retrieving read-only global configuration."""

from __future__ import annotations

from fastapi import APIRouter

from ..settings import settings

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/", response_model=dict)
async def get_config() -> dict:
    """Return global settings relevant for the frontend.

    Sensitive information such as passwords and tokens are omitted. Only
    human-readable configuration values are exposed.
    """
    return {
        "scheduler_timezone": settings.scheduler_timezone,
        "request_timeout": settings.request_timeout,
        "telegram_configured": bool(settings.telegram_token and settings.telegram_chat_id),
    }