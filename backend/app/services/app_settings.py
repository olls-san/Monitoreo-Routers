from __future__ import annotations

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AppSetting

TELEGRAM_SCHEDULE_KEY = "telegram_daily_summary_schedule"

DEFAULT_SCHEDULE = {
    "enabled": True,
    "hour": 9,
    "minute": 0,
    "timezone": "UTC",
}

async def get_setting_json(session: AsyncSession, key: str, default: Any = None) -> Any:
    row = await session.get(AppSetting, key)
    if not row or not row.value:
        return default
    try:
        return json.loads(row.value)
    except Exception:
        return default

async def set_setting_json(session: AsyncSession, key: str, value: Any) -> None:
    row = await session.get(AppSetting, key)
    s = json.dumps(value, ensure_ascii=False)
    if row:
        row.value = s
    else:
        session.add(AppSetting(key=key, value=s))
    await session.commit()

async def get_telegram_schedule(session: AsyncSession) -> dict:
    data = await get_setting_json(session, TELEGRAM_SCHEDULE_KEY, None)
    if not isinstance(data, dict):
        return DEFAULT_SCHEDULE.copy()

    # Merge con defaults para evitar faltantes
    merged = DEFAULT_SCHEDULE.copy()
    merged.update(data)
    return merged
