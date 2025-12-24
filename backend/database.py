"""Database configuration and session utilities for the MoniTe Web backend.

This module defines the asynchronous SQLAlchemy engine, session factory and a
context manager used to create and dispose of sessions when running tasks in
background workers such as the scheduler. It also exposes a simple
initialisation function to create all database tables on first run.

It relies on settings provided via `monite_web.backend.settings` using
`pydantic_settings.BaseSettings` so all configuration can be managed via
environment variables.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeMeta, declarative_base

from .settings import settings

# Base model for all SQLAlchemy models
Base: DeclarativeMeta = declarative_base()

# Create an async engine using SQLite. We explicitly disable the check_same_thread
# option because async drivers manage concurrency on their own. The echo flag
# can be toggled via environment variable if verbose SQL logging is needed.
engine = create_async_engine(
    settings.database_url,
    future=True,
    echo=settings.database_echo,
)

# Async sessionmaker bound to our engine. We enable expire_on_commit=False so
# objects remain usable after the transaction ends, which is helpful in
# FastAPI/async contexts.
async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Provide an async transactional scope around a series of operations.

    This helper is intended for use in background tasks (such as scheduled
    jobs) where dependency injection via FastAPI's request cycle is not
    available. It yields an `AsyncSession` and commits on success, rolling
    back on failure. Sessions are automatically closed.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Create database tables if they do not exist.

    When running under SQLite the DDL is executed on startup to ensure all
    tables are created. For production deployments with a more robust
    database the migration strategy should be handled by Alembic.
    """
    async with engine.begin() as conn:
        # Create all tables defined on the metadata
        await conn.run_sync(Base.metadata.create_all)