from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, List

from pydantic import BaseModel, ConfigDict, Field

from .models import ActionStatus


# ======================================================
# BASE CONFIG (OBLIGATORIA PARA Pydantic v2 + ORM)
# ======================================================

class ORMBaseModel(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


# =========================
# HOSTS
# =========================

class HostBase(ORMBaseModel):
    name: str
    ip: str
    username: str = "admin"

    # UI usa "type", DB usa "router_type"
    router_type: str = Field(default="MIKROTIK_ROUTEROS_REST", alias="type")

    enabled: bool = True
    notify_enabled: bool = True


class HostCreate(HostBase):
    password: Optional[str] = None
    port: int = 80


class HostUpdate(ORMBaseModel):
    name: Optional[str] = None
    ip: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    port: Optional[int] = None

    router_type: Optional[str] = Field(default=None, alias="type")
    enabled: Optional[bool] = None
    notify_enabled: Optional[bool] = None


class HostResponse(ORMBaseModel):
    id: int
    name: str
    ip: str
    username: str

    # Exponer "type" hacia UI
    type: str = Field(alias="router_type")

    enabled: bool = True
    notify_enabled: bool = True

    # Cache health
    last_online: Optional[bool] = None
    last_latency_ms: Optional[float] = None
    last_check_at: Optional[datetime] = None

    # Última acción
    last_action_key: Optional[str] = None
    last_action_at: Optional[datetime] = None
    last_action_status: Optional[str] = None


# =========================
# ACTION RUNS
# =========================

class ActionRunResponse(ORMBaseModel):
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

class AutomationRuleBase(ORMBaseModel):
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


class AutomationRuleUpdate(ORMBaseModel):
    host_id: Optional[int] = None
    action_key: Optional[str] = None
    cron: Optional[str] = None
    enabled: Optional[bool] = None
    retry_enabled: Optional[bool] = None
    retry_delay_minutes: Optional[int] = None
    max_attempts: Optional[int] = None
    telegram_enabled: Optional[bool] = None


class AutomationRuleResponse(AutomationRuleBase):
    id: int


# =========================
# HEALTH
# =========================

class HealthResponse(ORMBaseModel):
    host_id: int
    online: bool
    latency_ms: Optional[float]
    checked_at: datetime
    error: Optional[str] = None


class BatchHealthResponse(BaseModel):
    health: List[HealthResponse]
