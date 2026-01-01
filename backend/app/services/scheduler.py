"""Automation scheduler using APScheduler.

This module sets up an asynchronous scheduler for executing
automation rules defined in the database.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from ..config import settings
from ..database import get_async_session
from ..models import AutomationRule, Host
from ..services.action_runner import execute_and_record
from ..services.health_monitor import check_all_hosts, send_daily_summary
from ..services.app_settings import get_telegram_schedule
from ..services.telegram import send_alert, format_msg

logger = logging.getLogger(__name__)


class SchedulerService:
    """Service that manages scheduled automation jobs."""

    def __init__(self) -> None:
        self.scheduler = AsyncIOScheduler()

    async def start(self) -> None:
        """Start the scheduler and load jobs from the database."""
        self.scheduler.start()
        await self.load_jobs()

        # -------------------------
        # Health checks job
        # -------------------------
        try:
            interval_seconds = int(getattr(settings, "health_interval_seconds", 300) or 300)

            async def health_job() -> None:
                async for session in get_async_session():
                    async with session.begin():
                        await check_all_hosts(session)
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
            logger.exception("Failed to schedule health check job: %s", exc)

        # -------------------------
        # Daily summary job (DB configurable)
        # -------------------------
        try:
            await self.reschedule_daily_summary()
        except Exception as exc:
            logger.exception("Failed to schedule daily summary job: %s", exc)

    async def stop(self) -> None:
        """Stop the scheduler and remove all jobs."""
        try:
            self.scheduler.remove_all_jobs()
        finally:
            self.scheduler.shutdown()

    async def reschedule_daily_summary(self) -> None:
        """(Re)Schedule the daily summary job based on DB settings."""
        sched = None
        async for session in get_async_session():
            sched = await get_telegram_schedule(session)
            break

        enabled = bool((sched or {}).get("enabled", True))
        hour = int((sched or {}).get("hour", 9))
        minute = int((sched or {}).get("minute", 0))
        tz = str((sched or {}).get("timezone", getattr(settings, "scheduler_timezone", "UTC")))

        try:
            if self.scheduler.get_job("daily_summary"):
                self.scheduler.remove_job("daily_summary")
        except Exception:
            pass

        if not enabled:
            logger.info("Daily summary disabled by settings")
            return

        cron = CronTrigger(hour=hour, minute=minute, timezone=tz)

        async def summary_job() -> None:
            async for s in get_async_session():
                async with s.begin():
                    await send_daily_summary(s)
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

        logger.info("Daily summary scheduled at %02d:%02d (%s)", hour, minute, tz)

    async def load_jobs(self) -> None:
        """Load automation rules from the database and schedule them."""
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

        try:
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
        except Exception:
            pass

        async for session in get_async_session():
            rule: AutomationRule | None = await session.get(AutomationRule, rule_id)
            if not rule or not rule.enabled:
                return

            host: Host | None = await session.get(Host, rule.host_id)
            if not host:
                return

            schedule = (rule.schedule or "").strip()
            try:
                trigger = CronTrigger.from_crontab(schedule)
            except Exception as e:
                logger.error("Invalid cron schedule for rule %s: %r (%s)", rule_id, schedule, e)
                return

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
            start_utc = datetime.utcnow().isoformat() + "Z"

            last_run = None
            for attempt in range(1, attempts + 1):
                run = await execute_and_record(
                    session,
                    host,
                    rule.action_key,
                    attempt=attempt,
                    max_attempts=attempts,
                    telegram_enabled=rule.telegram_enabled,
                )
                last_run = run

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

            # -------------------------
            # Telegram (formato unificado) — resultado FINAL
            # -------------------------
            try:
                if rule.telegram_enabled and last_run is not None:
                    status_value = getattr(last_run.status, "value", last_run.status)
                    dur_ms = getattr(last_run, "duration_ms", None)
                    dur_txt = f"{dur_ms:.0f} ms" if isinstance(dur_ms, (int, float)) else "n/a"

                    schedule = (rule.schedule or "").strip() or "n/a"
                    action_key = rule.action_key or "n/a"

                    if status_value == "SUCCESS":
                        msg = format_msg(
                            title="⚙️ AUTOMATIZACIÓN — Ejecutada",
                            host_name=host.name,
                            host_ip=host.ip,
                            when=datetime.utcnow().isoformat() + "Z",
                            sections=[
                                ("🧩 Regla", [
                                    f"• ID: {rule_id}",
                                    f"• Cron: {schedule}",
                                    f"• Acción: {action_key}",
                                ]),
                                ("✅ Resultado", [
                                    f"• Estado: SUCCESS",
                                    f"• Intentos: 1/{attempts}",
                                    f"• Duración: {dur_txt}",
                                    f"• Inicio: {start_utc}",
                                ]),
                            ],
                            suggested=[
                                "Si esperabas otro resultado, revisar la regla y el cron",
                                "Ver el historial de acciones para detalle",
                            ],
                            footer="⚙️ Origen: Scheduler",
                        )
                        await send_alert(host.id, f"auto_{rule_id}_success", msg)

                    else:
                        err = getattr(last_run, "error_message", None) or getattr(last_run, "stderr", None) or "n/a"
                        msg = format_msg(
                            title="🚫 AUTOMATIZACIÓN — Falló",
                            host_name=host.name,
                            host_ip=host.ip,
                            when=datetime.utcnow().isoformat() + "Z",
                            sections=[
                                ("🧩 Regla", [
                                    f"• ID: {rule_id}",
                                    f"• Cron: {schedule}",
                                    f"• Acción: {action_key}",
                                ]),
                                ("❌ Resultado", [
                                    f"• Estado: {status_value}",
                                    f"• Intentos: {attempts}/{attempts}",
                                    f"• Duración: {dur_txt}",
                                    f"• Inicio: {start_utc}",
                                ]),
                                ("🧯 Error", [
                                    f"• {str(err)[:400]}",
                                ]),
                            ],
                            suggested=[
                                "Revisar conectividad / VPN / energía",
                                "Ejecutar la acción manualmente desde el panel",
                            ],
                            footer="⚙️ Origen: Scheduler",
                        )
                        await send_alert(host.id, f"auto_{rule_id}_fail", msg)

            except Exception as exc:
                logger.exception("Failed to send automation result telegram for rule %s: %s", rule_id, exc)

            break
