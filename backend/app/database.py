"""Database configuration and session management.

This module creates an asynchronous SQLAlchemy engine and session
factory bound to the configured database URL. Other modules
should import and use the :func:`get_async_session` dependency
to acquire a session inside FastAPI routes or background tasks.

The database is initialised when the application starts; tables
are created automatically on startup for convenience. In a
production deployment you might wish to use proper migrations
instead of auto-creating tables.
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from .config import settings

logger = logging.getLogger(__name__)

# Create the asynchronous engine.
engine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True,
)

# Create a session factory. expire_on_commit=False is important
# because it prevents attributes from being expired after commit,
# which can cause lazy-loading to fail in async contexts. See
# FastAPI docs and SQLAlchemy best practices【336215838796312†L83-L90】.
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base class for declarative models.
Base = declarative_base()


async def init_db() -> None:
    """Initialise the database by creating all tables.

    This function should be called once at application startup. It
    runs the synchronous metadata creation in an asynchronous
    context using run_sync().
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created")


async def get_async_session() -> AsyncSession:
    """Provide a transactional scope around a series of operations.

    This dependency yields an AsyncSession instance and ensures
    it is properly closed after use. The one session per request
    pattern aligns with SQLAlchemy async best practices【336215838796312†L265-L270】.
    """
    """FastAPI dependency that yields a DB session."""
    async with AsyncSessionLocal() as session:
        yield session

