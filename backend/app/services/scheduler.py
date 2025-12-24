"""Automation scheduler using APScheduler.

This module sets up an asynchronous scheduler for executing
automation rules defined in the database. Each rule schedules a
job that periodically executes an action on a host according to
its cron or interval specification. Retries and alerts are
handled within the job function.
"""

from __future__ import annotations

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from ..database import get_async_session
from ..models import AutomationRule, Host
from ..services.action_runner import execute_and_record
from ..services.health_monitor import check_all_hosts, send_daily_summary
from ..config import settings

logger = logging.getLogger(__name__)


class SchedulerService:
    """Service that manages scheduled automation jobs."""

    def __init__(self) -> None:
        self.scheduler = AsyncIOScheduler()

    async def start(self) -> None:
        """Start the scheduler and load jobs from the database."""
        self.scheduler.start()
        await self.load_jobs()
        # Schedule periodic health checks for all hosts
        try:
            interval_seconds = int(getattr(settings, "health_interval_seconds", 300) or 300)
            # Define async job wrapper for health checks
            async def health_job() -> None:
                async for session in get_async_session():
                    # run within a transaction
                    async with session.begin():
                        await check_all_hosts(session)
                        # commit is handled by session.begin context
                    break
            self.scheduler.add_job(
                health_job,
                trigger=IntervalTrigger(seconds=interval_seconds),
                id="health_check",
                replace_existing=True,
                max_instances=1,
                coalesce=True,
                misfire_grace_time=60,
            )
        except Exception as exc:
            # Log but do not prevent app startup
            import logging
            logging.getLogger(__name__).exception("Failed to schedule health check job: %s", exc)

        # Schedule daily summary via Telegram
        try:
            hour = int(getattr(settings, "telegram_daily_summary_hour", 9) or 9)
            minute = int(getattr(settings, "telegram_daily_summary_minute", 0) or 0)
            tz = getattr(settings, "scheduler_timezone", "UTC")
            cron = CronTrigger(hour=hour, minute=minute, timezone=tz)
            async def summary_job() -> None:
                async for session in get_async_session():
                    async with session.begin():
                        await send_daily_summary(session)
                    break
            self.scheduler.add_job(
                summary_job,
                trigger=cron,
                id="daily_summary",
                replace_existing=True,
                max_instances=1,
                coalesce=True,
                misfire_grace_time=600,
            )
        except Exception as exc:
            import logging
            logging.getLogger(__name__).exception("Failed to schedule daily summary job: %s", exc)

    async def stop(self) -> None:
        """Stop the scheduler and remove all jobs."""
        try:
            self.scheduler.remove_all_jobs()
        finally:
            self.scheduler.shutdown()

    async def load_jobs(self) -> None:
        """Load automation rules from the database and schedule them."""
        # get_async_session() is an async generator (FastAPI dependency style),
        # so we consume it with async for ... break
        async for session in get_async_session():
            result = await session.execute(
                select(AutomationRule.id).where(AutomationRule.enabled == True)
            )
            rule_ids = [row[0] for row in result.all()]
            break

        for rule_id in rule_ids:
            await self.add_job(rule_id)

        logger.info("Loaded %d automation jobs", len(self.scheduler.get_jobs()))

    async def add_job(self, rule_id: int) -> None:
        """Add a job for a given automation rule."""
        job_id = f"automation-{rule_id}"

        # Remove existing job if present (avoid duplication)
        try:
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
        except Exception:
            pass

        # Load rule to decide scheduling
        async for session in get_async_session():
            rule: AutomationRule | None = await session.get(AutomationRule, rule_id)
            if not rule or not rule.enabled:
                return

            # Validate host exists (optional, but keeps logs clean)
            host: Host | None = await session.get(Host, rule.host_id)
            if not host:
                return

            schedule = (rule.schedule or "").strip()
            try:
                trigger = CronTrigger.from_crontab(schedule)
            except Exception as e:
                logger.error("Invalid cron schedule for rule %s: %r (%s)", rule_id, schedule, e)
                return

            # Define async job wrapper (must be sync-callable by APScheduler, but can be async)
            async def job_wrapper() -> None:
                await self._run_rule(rule_id)

            self.scheduler.add_job(job_wrapper, trigger=trigger, id=job_id)
            break

        logger.info("Scheduled automation rule %s", rule_id)

    async def _run_rule(self, rule_id: int) -> None:
        """Execute an automation rule with retries."""
        async for session in get_async_session():
            rule: AutomationRule | None = await session.get(AutomationRule, rule_id)
            if not rule or not rule.enabled:
                logger.warning("Rule %s disabled or missing; skipping", rule_id)
                return

            host: Host | None = await session.get(Host, rule.host_id)
            if not host or not host.enabled:
                logger.warning("Host %s disabled or missing; skipping rule %s", rule.host_id, rule_id)
                return

            attempts = rule.max_attempts if rule.retry_enabled else 1

            for attempt in range(1, attempts + 1):
                run = await execute_and_record(
                    session,
                    host,
                    rule.action_key,
                    attempt=attempt,
                    max_attempts=attempts,
                    telegram_enabled=rule.telegram_enabled,
                )

                # run.status is Enum in our model -> compare using .value
                status_value = getattr(run.status, "value", run.status)
                if status_value == "SUCCESS":
                    break

                if attempt < attempts:
                    delay = int(rule.retry_delay_minutes or 10) * 60
                    logger.info(
                        "Retrying action %s on host %s in %s minutes (attempt %s/%s)",
                        rule.action_key, host.id, int(rule.retry_delay_minutes or 10),
                        attempt + 1, attempts,
                    )
                    await asyncio.sleep(delay)
            break
