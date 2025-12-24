"""Service functions for executing actions against hosts and recording results."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..drivers.base import get_driver
from ..models import ActionRun, ActionStatus, Host


async def execute_action(
    session: AsyncSession,
    host: Host,
    action_key: str,
    params: Optional[Dict[str, Any]] = None,
) -> ActionRun:
    """Execute an action on a host using its registered driver.

    This function wraps the driver invocation and ensures that an
    `ActionRun` record is persisted regardless of success or failure. On
    success, the status is set to `SUCCESS` and both the raw and parsed
    responses are stored. On failure, the status is `FAIL` and the error
    message is recorded.
    """
    # Always create the ActionRun record upfront.  We set default values
    # here and update them based on the driver result or error below.
    run = ActionRun(host_id=host.id, action_key=action_key)
    try:
        # Look up the driver – may raise ValueError if not registered
        driver = get_driver(host)
        result = await driver.execute(action_key, params)
        # Extract raw and parsed payloads
        raw = result.get("raw")
        parsed = result.get("parsed")
        # Serialise raw to a JSON string for SQLite compatibility
        run.response_raw = json.dumps(raw, ensure_ascii=False, default=str)
        run.response_parsed = parsed
        run.status = ActionStatus.SUCCESS
        run.error_message = None
    except Exception as exc:
        # Any exception results in a failed run.  We record the error
        # message and serialise it as a JSON object in response_raw for
        # consistency.  response_parsed remains None.
        run.status = ActionStatus.FAIL
        run.error_message = str(exc)
        run.response_raw = json.dumps({"error": str(exc)}, ensure_ascii=False, default=str)
        run.response_parsed = None
    # Persist the run (even on failure).  Commit is handled by the caller.
    session.add(run)
    return run