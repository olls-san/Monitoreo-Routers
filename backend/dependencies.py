"""Dependency providers for FastAPI routers."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .database import async_session_factory


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that yields a database session."""
    async with async_session_factory() as session:
        yield session