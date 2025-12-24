"""SQLAlchemy models for MoniTe Web.

These models define the database schema for hosts (routers),
action execution history and automation rules. Relationships
between tables are declared so that joined queries can be
performed easily via SQLAlchemy ORM.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
    Float,
)
from sqlalchemy.orm import relationship, synonym
from sqlalchemy.orm import synonym

from .database import Base


class RouterType(str, enum.Enum):
    """Enumeration of supported router types.

    The value stored in the database is the key used to select
    the appropriate driver. Additional types can be added here
    without affecting existing data.
    """

    MIKROTIK_ROUTEROS_REST = "MIKROTIK_ROUTEROS_REST"
    # Future types: HUAWEI_*, ZTE_*, GENERIC_SSH etc.


class ActionStatus(str, enum.Enum):
    """Status of an action execution."""

    SUCCESS = "SUCCESS"
    FAIL = "FAIL"


class Host(Base):
    """Represents a physical or virtual router that can be managed.

    Credentials are stored in the database. For real production
    deployments you should use a secrets manager or encryption
    service to protect passwords, but for simplicity we persist
    them directly. Use the `password` field carefully.
    """

    __tablename__ = "hosts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    ip = Column(String, nullable=False)
    username = Column(String, nullable=False, default="admin")
    password = Column(String, nullable=True)
    port = Column(Integer, nullable=False, default=80)
    router_type = Column(String, nullable=False, default=RouterType.MIKROTIK_ROUTEROS_REST.value)
    enabled = Column(Boolean, nullable=False, default=True)

    # Cache fields for last known health status. These provide
    # a quick way to retrieve the most recent check results
    # without querying the history table. They are nullable
    # because a host may never have been checked.
    last_status = Column(String, nullable=True, index=True)
    last_checked_at = Column(DateTime, nullable=True, index=True)
    last_latency_ms = Column(Float, nullable=True)

    # Whether this host should send Telegram alerts on state change or
    # action failures. Defaults to True. Can be toggled via API.
    notify_enabled = Column(Boolean, nullable=False, default=True)

    # Relationships
    runs = relationship("ActionRun", back_populates="host", cascade="all, delete-orphan")
    automation_rules = relationship("AutomationRule", back_populates="host", cascade="all, delete-orphan")

    # History of health checks for this host. Populated by the health
    # monitoring service whenever a check is performed. Cascade
    # deletion ensures health rows are removed if the host is deleted.
    health_checks = relationship("HostHealth", back_populates="host", cascade="all, delete-orphan")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Host id={self.id} name={self.name} ip={self.ip}>"


class ActionRun(Base):
    """History of executed actions.

    Each time an action is invoked on a host, a record is
    created. The response_parsed column stores structured
    information extracted from the raw response, such as data
    balance and validity for USSD logs.
    """

    __tablename__ = "action_runs"

    id = Column(Integer, primary_key=True, index=True)
    host_id = Column(Integer, ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False)
    router_type = Column(String, nullable=False)
    action_key = Column(String, nullable=False)
    # Timestamp when the action began executing. Previously named
    # ``executed_at``. Kept for backwards compatibility – in new
    # records this represents the start time.
    started_at = Column(DateTime, default=datetime.utcnow)
    # Backwards compatible alias for started_at. Many legacy parts of the
    # code refer to ``executed_at``. We map it via a SQLAlchemy
    # synonym so that both attribute names point to the same column.
    executed_at = synonym("started_at")

    # Timestamp when the action finished. Nullable until completion.
    finished_at = Column(DateTime, nullable=True)

    # Total duration of the action in milliseconds. Nullable until
    # completion or when duration cannot be measured.
    duration_ms = Column(Float, nullable=True)

    # Status of the run: SUCCESS or FAIL. Defaults to SUCCESS.
    status = Column(String, nullable=False, default=ActionStatus.SUCCESS.value)

    # Captured output streams from the action execution. Drivers can
    # populate these if applicable. For HTTP-based drivers the
    # response body may be stored here.
    stdout = Column(Text, nullable=True)
    stderr = Column(Text, nullable=True)

    # Parsed structured data extracted from the action response.
    response_parsed = Column(JSON, nullable=True)

    # Raw unprocessed response from the router or driver. Included
    # for completeness and backwards compatibility with earlier
    # versions of the API.
    response_raw = Column(Text, nullable=True)

    # Error message if the action failed. Populated when status = FAIL.
    error_message = Column(String, nullable=True)

    host = relationship("Host", back_populates="runs")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ActionRun id={self.id} host_id={self.host_id} action={self.action_key}>"


class AutomationRule(Base):
    """Rules that define automated execution of actions.

    APScheduler uses the schedule string to configure cron or
    interval jobs. The retry fields control how many times a
    failing action will be re-attempted before sending alerts.
    """

    __tablename__ = "automation_rules"

    id = Column(Integer, primary_key=True, index=True)
    host_id = Column(Integer, ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False)
    action_key = Column(String, nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    schedule = Column(String, nullable=False)  # Cron expression or interval spec
    timeout_seconds = Column(Integer, nullable=True, default=60)
    retry_enabled = Column(Boolean, nullable=False, default=True)
    retry_delay_minutes = Column(Integer, nullable=False, default=10)
    max_attempts = Column(Integer, nullable=False, default=2)
    telegram_enabled = Column(Boolean, nullable=False, default=True)

    host = relationship("Host", back_populates="automation_rules")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AutomationRule id={self.id} host_id={self.host_id} action={self.action_key}>"


# -----------------------------------------------------------------------------
# Health monitoring models
# -----------------------------------------------------------------------------

class HostHealth(Base):
    """History of host health checks.

    Each record represents a single connectivity check for a host. It stores
    the outcome (online/offline), the measured latency in milliseconds and
    any error message captured during the check. Timestamp is stored in
    ``checked_at``.
    """

    __tablename__ = "host_health"

    id = Column(Integer, primary_key=True, index=True)
    host_id = Column(Integer, ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String, nullable=False, index=True)  # e.g. "online" or "offline"
    latency_ms = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    checked_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationship back to Host
    host = relationship("Host", back_populates="health_checks")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<HostHealth id={self.id} host_id={self.host_id} status={self.status} at={self.checked_at}>"
