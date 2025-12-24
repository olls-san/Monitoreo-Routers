"""API endpoints for automation rules."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_async_session
from ..models import AutomationRule
from ..schemas import (
    AutomationRuleCreate,
    AutomationRuleResponse,
    AutomationRuleUpdate,
)
from ..services.scheduler import SchedulerService

# The canonical prefix for automation rules.  Renamed from "automation"
# to "automation-rules" to align with the frontend contract and avoid
# ambiguity with other automation‑related resources.
router = APIRouter(prefix="/automation-rules", tags=["automation"])

# We'll create a singleton scheduler instance. It will be started in main.py.
scheduler_service: SchedulerService | None = None


@router.get("/", response_model=List[AutomationRuleResponse])
async def list_rules(session: AsyncSession = Depends(get_async_session)) -> List[AutomationRule]:
    result = await session.execute(select(AutomationRule))
    rules = result.scalars().all()
    return rules


@router.post("/", response_model=AutomationRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(payload: AutomationRuleCreate, session: AsyncSession = Depends(get_async_session)) -> AutomationRule:
    rule = AutomationRule(**payload.model_dump())
    session.add(rule)
    await session.commit()
    await session.refresh(rule)
    # schedule job if scheduler is available
    if scheduler_service:
        await scheduler_service.add_job(rule.id)
    return rule


@router.put("/{rule_id}", response_model=AutomationRuleResponse)
async def update_rule(rule_id: int, payload: AutomationRuleUpdate, session: AsyncSession = Depends(get_async_session)) -> AutomationRule:
    rule = await session.get(AutomationRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    await session.commit()
    await session.refresh(rule)
    if scheduler_service:
        await scheduler_service.add_job(rule.id)
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(rule_id: int, session: AsyncSession = Depends(get_async_session)) -> None:
    rule = await session.get(AutomationRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    await session.delete(rule)
    await session.commit()
    # remove job from scheduler
    if scheduler_service:
        job_id = f"automation-{rule_id}"
        try:
            scheduler_service.scheduler.remove_job(job_id)
        except Exception:
            pass
