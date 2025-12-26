"""Database configuration and session management (async).

Fixes for SQLite concurrency:
- WAL mode
- busy_timeout
- connect timeout
- rollback on exceptions
"""

from __future__ import annotations

import logging

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool

from .config import settings

logger = logging.getLogger(__name__)


def _make_engine():
    url = settings.database_url

    # ✅ SQLite async: configurar para concurrencia más estable
    if url.startswith("sqlite+aiosqlite"):
        return create_async_engine(
            url,
            echo=False,
            future=True,
            poolclass=NullPool,  # evita reuso de conexiones en sqlite (reduce locks)
            connect_args={
                "check_same_thread": False,
                "timeout": 30,  # espera hasta 30s por locks
            },
        )

    # Otros motores: pool normal
    return create_async_engine(
        url,
        echo=False,
        future=True,
    )


engine = _make_engine()


# ✅ PRAGMAs SQLite: WAL + busy_timeout
if settings.database_url.startswith("sqlite+aiosqlite"):

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA busy_timeout=30000;")  # 30s
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.close()


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


async def get_async_session() -> AsyncSession:
    """FastAPI dependency that yields a DB session (safe rollback)."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
