"""API endpoints for managing automation rules."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_session
from ..models import AutomationRule, Host
from ..schemas import (
    AutomationRuleCreate,
    AutomationRuleUpdate,
    AutomationRuleResponse,
)
from ..services.automation import schedule_rule, remove_rule_job


router = APIRouter(prefix="/automation-rules", tags=["automation_rules"])


@router.get("/", response_model=List[AutomationRuleResponse])
async def list_rules(session: AsyncSession = Depends(get_session)) -> List[AutomationRuleResponse]:
    result = await session.execute(select(AutomationRule))
    rules = result.scalars().all()
    return [AutomationRuleResponse.model_validate(rule) for rule in rules]


@router.post("/", response_model=AutomationRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(rule_in: AutomationRuleCreate, session: AsyncSession = Depends(get_session)) -> AutomationRuleResponse:
    # Validate host exists
    host = await session.get(Host, rule_in.host_id)
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    # Use model_dump to ensure compatibility with Pydantic v2
    rule_data = rule_in.model_dump()
    rule = AutomationRule(**rule_data)
    session.add(rule)
    await session.commit()
    await session.refresh(rule)
    if rule.enabled:
        schedule_rule(rule)
    return AutomationRuleResponse.model_validate(rule)


@router.get("/{rule_id}", response_model=AutomationRuleResponse)
async def get_rule(rule_id: int, session: AsyncSession = Depends(get_session)) -> AutomationRuleResponse:
    rule = await session.get(AutomationRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Automation rule not found")
    return AutomationRuleResponse.model_validate(rule)


@router.put("/{rule_id}", response_model=AutomationRuleResponse)
async def update_rule(rule_id: int, rule_in: AutomationRuleUpdate, session: AsyncSession = Depends(get_session)) -> AutomationRuleResponse:
    rule = await session.get(AutomationRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Automation rule not found")
    # If host_id is changing, validate new host exists
    if rule_in.host_id is not None and rule_in.host_id != rule.host_id:
        host = await session.get(Host, rule_in.host_id)
        if not host:
            raise HTTPException(status_code=404, detail="Host not found")
    # Remove existing scheduled job if any
    remove_rule_job(rule_id)
    # Use model_dump with exclude_unset to get only provided fields
    for field, value in rule_in.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    await session.commit()
    await session.refresh(rule)
    if rule.enabled:
        schedule_rule(rule)
    return AutomationRuleResponse.model_validate(rule)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(rule_id: int, session: AsyncSession = Depends(get_session)) -> None:
    rule = await session.get(AutomationRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Automation rule not found")
    remove_rule_job(rule_id)
    await session.delete(rule)
    await session.commit()