from __future__ import annotations

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field

from ..database import get_async_session
from ..services.app_settings import get_telegram_schedule, set_setting_json, TELEGRAM_SCHEDULE_KEY

from ..services.app_settings import (
    get_telegram_severity,
    set_setting_json,
    TELEGRAM_SEVERITY_KEY,
    DEFAULT_SEVERITY,
)


router = APIRouter(prefix="/settings", tags=["settings"])

class TelegramScheduleIn(BaseModel):
    enabled: bool = True
    hour: int = Field(ge=0, le=23)
    minute: int = Field(ge=0, le=59)
    timezone: str = "UTC"

class SeverityBand(BaseModel):
    days: int = Field(ge=0, le=365)
    data_mb: int = Field(ge=0, le=10_000_000)

class SeverityThresholdsIn(BaseModel):
    critical: SeverityBand
    high: SeverityBand
    medium: SeverityBand


@router.get("/telegram-schedule", response_model=dict)
async def get_schedule():
    async for session in get_async_session():
        data = await get_telegram_schedule(session)
        break
    return data

@router.put("/telegram-schedule", response_model=dict)
async def update_schedule(payload: TelegramScheduleIn, request: Request):
    # Guardar en DB
    async for session in get_async_session():
        await set_setting_json(session, TELEGRAM_SCHEDULE_KEY, payload.model_dump())
        break

    # Reprogramar scheduler en caliente
    svc = getattr(request.app.state, "scheduler_service", None)
    if not svc:
        raise HTTPException(status_code=500, detail="Scheduler service not available")

    await svc.reschedule_daily_summary()

    return payload.model_dump()

@router.get("/telegram-severity", response_model=dict)
async def get_severity():
    async for session in get_async_session():
        data = await get_telegram_severity(session)
        break
    return data

@router.put("/telegram-severity", response_model=dict)
async def update_severity(payload: SeverityThresholdsIn):
    async for session in get_async_session():
        await set_setting_json(session, TELEGRAM_SEVERITY_KEY, payload.model_dump())
        break
    return payload.model_dump()
