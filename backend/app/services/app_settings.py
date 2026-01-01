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

TELEGRAM_SEVERITY_KEY = "telegram_severity_thresholds"

DEFAULT_SEVERITY = {
    "critical": {"days": 1, "data_mb": 300},
    "high": {"days": 3, "data_mb": 1024},
    "medium": {"days": 7, "data_mb": 2048},
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

async def get_telegram_severity(session: AsyncSession) -> dict:
    data = await get_setting_json(session, TELEGRAM_SEVERITY_KEY, None)
    if not isinstance(data, dict):
        return DEFAULT_SEVERITY.copy()

    merged = DEFAULT_SEVERITY.copy()
    # merge profundo básico
    for k in ["critical", "high", "medium"]:
        if isinstance(data.get(k), dict):
            merged[k] = {**merged[k], **data[k]}
    return merged
