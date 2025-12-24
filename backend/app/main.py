"""MoniTe Web backend application entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .routers import hosts, actions, automation, history, config
from .services.scheduler import SchedulerService

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Instantiate the scheduler service. It will be started on startup.
scheduler_service = SchedulerService()

# Make scheduler available to automation router
automation.scheduler_service = scheduler_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise resources when the app starts and release them when shutting down."""
    # Create database tables
    await init_db()

    # Start scheduler (NO tumbar la app si falla)
    try:
        await scheduler_service.start()
        logger.info("Scheduler started")
    except Exception:
        logger.exception("Scheduler failed to start (continuing without scheduler)")

    try:
        yield
    finally:
        try:
            await scheduler_service.stop()
            logger.info("Scheduler stopped")
        except Exception:
            logger.exception("Scheduler failed to stop cleanly")


app = FastAPI(title="MoniTe Web API", lifespan=lifespan)

# ✅ CORS for local dev (React/Vite)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers (sin prefijo /api)
app.include_router(hosts.router)
app.include_router(actions.router)
app.include_router(automation.router)
app.include_router(history.router)
app.include_router(config.router)

# Root endpoint
@app.get("/")
async def root():
    return {"message": "MoniTe Web backend is running"}
