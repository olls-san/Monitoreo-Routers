from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db, engine
from .routers import hosts, actions, automation, history, config
from .services.scheduler import SchedulerService
from .routers import settings as settings_router

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
        app.state.scheduler_service = scheduler_service
    except Exception:
        logger.exception("Scheduler failed to start (continuing without scheduler)")

    try:
        yield
    finally:
        # Stop scheduler
        try:
            await scheduler_service.stop()
            logger.info("Scheduler stopped")
        except Exception:
            logger.exception("Scheduler failed to stop cleanly")

        # ✅ IMPORTANT: Dispose DB engine to close pooled connections cleanly
        # This helps prevent noisy errors like:
        # "AsyncAdaptedQueuePool: Exception during reset or similar"
        try:
            await engine.dispose()
            logger.info("DB engine disposed")
        except Exception:
            logger.exception("Failed to dispose DB engine")


app = FastAPI(title="MoniTe Web API", lifespan=lifespan)

# ✅ CORS for local dev + LAN access
# Ajusta/añade tu IP si cambia
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://192.168.188.165:5173",
    ],
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
app.include_router(settings_router.router)

# Root endpoint
@app.get("/")
async def root():
    return {"message": "MoniTe Web backend is running"}
