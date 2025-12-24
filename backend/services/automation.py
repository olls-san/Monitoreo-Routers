"""Automation scheduling and execution logic."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import session_scope
from ..models import AutomationRule, Host
from ..services.actions import execute_action
from ..services.telegram import send_alert


async def run_rule(rule_id: int, attempt: int = 1) -> None:
    """Execute a single automation rule by ID.

    This helper runs inside the scheduler. It retrieves the rule and its host
    from the database, executes the associated action and handles retries and
    Telegram notifications.
    """
    async with session_scope() as session:
        rule = await session.get(AutomationRule, rule_id)
        # Rule might have been removed or disabled since scheduling
        if not rule or not rule.enabled:
            return
        host = await session.get(Host, rule.host_id)
        if not host:
            return
        run = await execute_action(session, host, rule.action_key)
        # Immediately commit so that the run is persisted
        await session.commit()
        # Send notifications
        if rule.telegram_enabled:
            status = run.status.value
            msg = f"Automation {rule.id} ({rule.action_key}) on host {host.name} {status.lower()}."
            if run.error_message:
                msg += f" Error: {run.error_message}"
            await send_alert(host, f"automation_{rule.action_key}_{status.lower()}", msg)
        # Handle retries
        from ..models import ActionStatus
        if run.status == ActionStatus.FAIL and rule.retry_enabled and attempt < rule.max_attempts:
            delay = timedelta(minutes=rule.retry_delay_minutes)
            scheduler = get_scheduler()
            run_date = datetime.now(timezone.utc) + delay
            # schedule another attempt
            scheduler.add_job(
                run_rule,
                args=[rule.id, attempt + 1],
                trigger="date",
                run_date=run_date,
            )


_scheduler: Optional[AsyncIOScheduler] = None


def get_scheduler() -> AsyncIOScheduler:
    """Return the global AsyncIOScheduler instance, creating it if needed."""
    global _scheduler
    if _scheduler is None:
        # Initialise scheduler with configured timezone. If settings.scheduler_timezone is
        # invalid, AsyncIOScheduler will fall back to system default.
        from ..settings import settings
        _scheduler = AsyncIOScheduler(timezone=settings.scheduler_timezone)
    return _scheduler


async def schedule_existing_rules() -> None:
    """Schedule all enabled automation rules found in the database."""
    scheduler = get_scheduler()
    async with session_scope() as session:
        result = await session.execute(select(AutomationRule).where(AutomationRule.enabled == True))
        rules = result.scalars().all()
        for rule in rules:
            schedule_rule(rule)


def schedule_rule(rule: AutomationRule) -> None:
    """Schedule a single automation rule using APScheduler."""
    scheduler = get_scheduler()
    trigger = CronTrigger.from_crontab(rule.cron)
    scheduler.add_job(run_rule, trigger=trigger, args=[rule.id])


def remove_rule_job(rule_id: int) -> None:
    """Remove any scheduled jobs associated with a rule.

    Jobs are identified by the function and arguments. APScheduler does not
    automatically replace jobs on update so they must be removed before
    re-adding.
    """
    scheduler = get_scheduler()
    for job in scheduler.get_jobs():
        if job.func == run_rule and job.args and job.args[0] == rule_id:
            job.remove()