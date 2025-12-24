"""Scheduler bootstrap for MoniTe Web."""

from __future__ import annotations

import logging

from .services.automation import get_scheduler, schedule_existing_rules

logger = logging.getLogger(__name__)


async def start_scheduler() -> None:
    """Start the APScheduler and register existing automation rules.

    This function is intended to be called during application startup. It
    gracefully handles errors during scheduler initialisation so the rest of
    the application can continue to run if the scheduler fails.
    """
    scheduler = get_scheduler()
    try:
        scheduler.start()
        await schedule_existing_rules()
    except Exception as exc:
        logger.exception("Failed to start scheduler: %s", exc)