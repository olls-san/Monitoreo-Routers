"""Pydantic models for request and response validation."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from .models import ActionStatus, RouterType


# ------------------------------- Host Schemas -------------------------------

class HostBase(BaseModel):
    name: str = Field(..., description="Friendly name of the router")
    ip: str = Field(..., description="IP address of the router")
    username: str = Field("admin", description="Username for authentication")
    password: Optional[str] = Field(None, description="Password for authentication")
    port: int = Field(80, description="HTTP port of the REST API")
    router_type: str = Field(RouterType.MIKROTIK_ROUTEROS_REST.value, description="Router type key")
    enabled: bool = Field(True, description="Whether the router is active")


class HostCreate(HostBase):
    pass


class HostUpdate(BaseModel):
    name: Optional[str] = None
    ip: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    port: Optional[int] = None
    router_type: Optional[str] = None
    enabled: Optional[bool] = None
    notify_enabled: Optional[bool] = None


class HostResponse(HostBase):
    id: int

    # Cache fields for quick status display
    last_status: Optional[str] = None
    last_checked_at: Optional[datetime] = None
    last_latency_ms: Optional[float] = None
    notify_enabled: bool = True

    class Config:
        orm_mode = True


# -------------------------- Automation Rule Schemas -------------------------

class AutomationRuleBase(BaseModel):
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


class AutomationRuleUpdate(BaseModel):
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

    class Config:
        orm_mode = True


# ---------------------------- Action Run Schemas ----------------------------

class ActionRunResponse(BaseModel):
    """Response schema for action run records.

    Includes timing information (start/finish/duration) and stdout/stderr
    streams in addition to the previous fields. The ``executed_at`` field
    is retained for backwards compatibility and mirrors ``started_at``.
    """

    id: int
    host_id: int
    router_type: str
    action_key: str
    # Start time of the action (previously ``executed_at``)
    started_at: datetime
    # Alias for backwards compatibility; maps to ``started_at``
    executed_at: datetime
    # Finish time of the action
    finished_at: Optional[datetime] = None
    # Total duration in milliseconds
    duration_ms: Optional[float] = None
    status: ActionStatus
    # Captured standard output and error streams
    stdout: Optional[Any] = None
    stderr: Optional[Any] = None
    # Parsed structured data and raw response from the driver
    response_parsed: Optional[Any] = None
    response_raw: Optional[Any] = None
    error_message: Optional[str] = None

    class Config:
        orm_mode = True


class HostHealthResponse(BaseModel):
    """Response schema for host health history entries."""

    id: int
    host_id: int
    status: str
    latency_ms: Optional[float] = None
    error_message: Optional[str] = None
    checked_at: datetime

    class Config:
        orm_mode = True


# ---------------------------- Execute Action Schema ----------------------------

class ExecuteActionRequest(BaseModel):
    """Request body for executing an arbitrary action on a host.

    The frontend sends an ``action_key`` identifying which action to run
    and an optional ``params`` dictionary containing any parameters
    required by the driver.  Parameters are passed through to the
    underlying driver without validation here; drivers should perform
    their own validation.
    """

    action_key: str = Field(..., description="Key identifying the action to execute")
    params: Optional[dict[str, Any]] = Field(default_factory=dict, description="Optional parameters for the action")
