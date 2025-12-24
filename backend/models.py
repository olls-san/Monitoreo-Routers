"""SQLAlchemy models for MoniTe Web.

This module defines the database schema using SQLAlchemy's declarative model. It
contains entities to represent hosts (routers), actions executed against them,
and automation rules that schedule actions periodically.
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .database import Base


class Host(Base):
    """Represents a network device (router) configured in the system."""

    __tablename__ = "hosts"

    id: int = Column(Integer, primary_key=True, index=True)
    name: str = Column(String, nullable=False)
    ip: str = Column(String, nullable=False)
    # Removed the port column. In the new architecture the service
    # always connects on the default API port for each driver.  Hosts are
    # uniquely identified by their IP address and type, so there is no
    # need to persist a separate port in the database.  Removing this
    # column requires recreating the database schema (or running a
    # migration) because SQLite cannot drop columns easily.
    # port: int = Column(Integer, nullable=False, default=80)
    type: str = Column(String, nullable=False)
    username: str = Column(String, nullable=False)
    password: str = Column(String, nullable=False)

    # Last known health state. None indicates unknown / never checked.
    last_online: bool | None = Column(Boolean, default=None)
    last_latency_ms: float | None = Column(Float, default=None)
    last_check_at: datetime | None = Column(DateTime(timezone=True), default=None)

    # Relationships
    action_runs = relationship(
        "ActionRun",
        back_populates="host",
        cascade="all, delete-orphan",
    )
    automation_rules = relationship(
        "AutomationRule",
        back_populates="host",
        cascade="all, delete-orphan",
    )


class ActionStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"
    FAIL = "FAIL"


class ActionRun(Base):
    """Represents a single execution of an action against a host."""

    __tablename__ = "action_runs"

    id: int = Column(Integer, primary_key=True, index=True)
    host_id: int = Column(Integer, ForeignKey("hosts.id"), nullable=False, index=True)
    action_key: str = Column(String, nullable=False, index=True)
    status: ActionStatus = Column(SAEnum(ActionStatus, name="status_enum"), nullable=False)
    # Raw response is stored as a JSON-encoded string. This avoids the sqlite3
    # issue where lists/dicts cannot be persisted directly. The client must
    # decode this field to view the original structure.
    response_raw: str | None = Column(Text, nullable=True)
    # Parsed response (if available) is stored as a JSON column.
    response_parsed: Any | None = Column(JSON, nullable=True)
    error_message: str | None = Column(String, nullable=True)
    executed_at: datetime = Column(
        DateTime(timezone=True), nullable=False,
        # Use timezone-aware UTC now as default to avoid naive datetime insertion into a timezone column
        default=lambda: datetime.now(timezone.utc),
    )

    host = relationship("Host", back_populates="action_runs")


class AutomationRule(Base):
    """Represents a scheduled action that runs on a host."""

    __tablename__ = "automation_rules"

    id: int = Column(Integer, primary_key=True, index=True)
    host_id: int = Column(Integer, ForeignKey("hosts.id"), nullable=False, index=True)
    action_key: str = Column(String, nullable=False)
    cron: str = Column(String, nullable=False)
    enabled: bool = Column(Boolean, default=True)
    retry_enabled: bool = Column(Boolean, default=False)
    retry_delay_minutes: int = Column(Integer, default=0)
    max_attempts: int = Column(Integer, default=1)
    telegram_enabled: bool = Column(Boolean, default=False)

    host = relationship("Host", back_populates="automation_rules")