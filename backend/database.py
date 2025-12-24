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

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool

from .config import settings

logger = logging.getLogger(__name__)

def _make_engine():
    url = settings.database_url

    # ✅ SQLite async: NullPool evita resets/rollbacks raros en shutdown
    if url.startswith("sqlite+aiosqlite"):
        return create_async_engine(
            url,
            echo=False,
            future=True,
            poolclass=NullPool,
        )

    # Otros motores (Postgres/MySQL) pueden usar pool normal
    return create_async_engine(
        url,
        echo=False,
        future=True,
    )

engine = _make_engine()

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()

async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created")

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency: 1 sesión por request, con rollback automático si hay excepción.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            # ✅ importante en async + sqlite
            await session.rollback()
            raise
        finally:
            await session.close()
