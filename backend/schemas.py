"""Pydantic models for MoniTe Web API schemas.

These classes define the request and response payloads exposed by the FastAPI
backend. All schemas derive from Pydantic's `BaseModel` and are configured
using `ConfigDict` to allow construction from ORM objects via
`from_attributes=True`. The models are purposefully separated into input
schemas (for creating/updating resources) and output schemas (for responses).
Sensitive fields such as passwords are excluded from response models.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .models import ActionStatus


# =========================
# HOSTS
# =========================

class HostBase(BaseModel):
    name: str
    ip: str
    type: str
    username: str


class HostCreate(HostBase):
    password: str


class HostUpdate(BaseModel):
    name: Optional[str] = None
    ip: Optional[str] = None
    type: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None


class HostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    ip: str
    type: str
    username: str
    last_online: Optional[bool] = None
    last_latency_ms: Optional[float] = None
    last_check_at: Optional[datetime] = None


# =========================
# ACTION RUNS
# =========================

class ActionRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    host_id: int
    action_key: str
    status: ActionStatus
    response_raw: Optional[str] = None
    response_parsed: Optional[Any] = None
    error_message: Optional[str] = None
    executed_at: datetime


# =========================
# AUTOMATIONS
# =========================

class AutomationRuleBase(BaseModel):
    host_id: int
    action_key: str
    cron: str
    enabled: bool = True
    retry_enabled: bool = False
    retry_delay_minutes: int = 0
    max_attempts: int = 1
    telegram_enabled: bool = False


class AutomationRuleCreate(AutomationRuleBase):
    pass


class AutomationRuleUpdate(BaseModel):
    host_id: Optional[int] = None
    action_key: Optional[str] = None
    cron: Optional[str] = None
    enabled: Optional[bool] = None
    retry_enabled: Optional[bool] = None
    retry_delay_minutes: Optional[int] = None
    max_attempts: Optional[int] = None
    telegram_enabled: Optional[bool] = None


class AutomationRuleResponse(AutomationRuleBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


# =========================
# HEALTH
# =========================

class HealthResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    host_id: int
    online: bool
    latency_ms: Optional[float]
    checked_at: datetime
    error: Optional[str] = None


class BatchHealthResponse(BaseModel):
    health: List[HealthResponse]
