"""Pydantic models for request and response validation."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from .models import ActionStatus, RouterType


# ======================================================
# Base: Pydantic v2 + ORM + alias support
# ======================================================

class ORMModel(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


# ------------------------------- Host Schemas -------------------------------

class HostBase(ORMModel):
    name: str = Field(..., description="Friendly name of the router")
    ip: str = Field(..., description="IP address of the router")
    username: str = Field("admin", description="Username for authentication")
    password: Optional[str] = Field(None, description="Password for authentication")
    port: int = Field(80, description="HTTP port of the REST API")

    # DB/model usa router_type, UI suele enviar/leer "type"
    router_type: str = Field(
        default=RouterType.MIKROTIK_ROUTEROS_REST.value,
        alias="type",
        description="Router type key",
    )

    enabled: bool = Field(True, description="Whether the router is active")
    notify_enabled: bool = Field(True, description="Whether telegram notifications are enabled")


class HostCreate(HostBase):
    pass


class HostUpdate(ORMModel):
    name: Optional[str] = None
    ip: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    port: Optional[int] = None

    router_type: Optional[str] = Field(default=None, alias="type")
    enabled: Optional[bool] = None
    notify_enabled: Optional[bool] = None


class HostResponse(ORMModel):
    id: int

    # Campos base (mismos de HostBase, pero no heredamos para evitar
    # que password sea "requerido" en response según algunas validaciones)
    name: str
    ip: str
    username: str
    port: int
    enabled: bool
    notify_enabled: bool

    # Exponer "type" a la UI (alias de router_type en DB)
    type: str = Field(alias="router_type")

    # Cache fields en DB (los nombres reales del modelo)
    last_status: Optional[str] = None
    last_checked_at: Optional[datetime] = None
    last_latency_ms: Optional[float] = None

    # Campos que la UI usa (compatibilidad)
    last_online: Optional[bool] = None
    last_check_at: Optional[datetime] = None
    last_latency_ms_ui: Optional[float] = Field(default=None, alias="last_latency_ms")

    # Last action summary (derived from action history)
    last_action_key: Optional[str] = None
    last_action_at: Optional[datetime] = None
    last_action_status: Optional[str] = None


# -------------------------- Automation Rule Schemas -------------------------

class AutomationRuleBase(ORMModel):
    host_id: int
    action_key: str
    schedule: str = Field(..., description="Cron expression (e.g. '*/10 * * * *')")
    enabled: bool = True
    timeout_seconds: Optional[int] = 60
    retry_enabled: bool = True
    retry_delay_minutes: int = 10
    max_attempts: int = 2
    telegram_enabled: bool = True


class AutomationRuleCreate(AutomationRuleBase):
    pass


class AutomationRuleUpdate(ORMModel):
    host_id: Optional[int] = None
    action_key: Optional[str] = None
    schedule: Optional[str] = None
    enabled: Optional[bool] = None
    timeout_seconds: Optional[int] = None
    retry_enabled: Optional[bool] = None
    retry_delay_minutes: Optional[int] = None
    max_attempts: Optional[int] = None
    telegram_enabled: Optional[bool] = None


class AutomationRuleResponse(AutomationRuleBase):
    id: int


# ---------------------------- Action Run Schemas ----------------------------

class ActionRunResponse(ORMModel):
    """Response schema for action run records."""

    id: int
    host_id: int
    router_type: str
    action_key: str

    started_at: datetime
    executed_at: datetime  # alias compatible (mismo valor en router)
    finished_at: Optional[datetime] = None
    duration_ms: Optional[float] = None

    status: ActionStatus
    stdout: Optional[Any] = None
    stderr: Optional[Any] = None
    response_parsed: Optional[Any] = None
    response_raw: Optional[Any] = None
    error_message: Optional[str] = None


class HostHealthResponse(ORMModel):
    """Response schema for host health history entries."""

    id: int
    host_id: int
    status: str
    latency_ms: Optional[float] = None
    error_message: Optional[str] = None
    checked_at: datetime


# ---------------------------- Execute Action Schema ----------------------------

class ExecuteActionRequest(BaseModel):
    action_key: str = Field(..., description="Key identifying the action to execute")
    params: Optional[dict[str, Any]] = Field(
        default_factory=dict,
        description="Optional parameters for the action",
    )
