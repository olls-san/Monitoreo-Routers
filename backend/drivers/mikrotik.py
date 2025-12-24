"""MikroTik REST driver implementation.

This driver implements the actions specified in the MVP for MikroTik routers.
It uses the built-in REST API provided by MikroTik (since RouterOS 7) to
execute USSD commands and retrieve logs. A Basic Auth header is used for
authentication. All HTTP interactions are wrapped in a context manager to
ensure proper cleanup of the client.
"""

from __future__ import annotations

import base64
import json
import re
from typing import Any, Dict, Optional, Tuple

import httpx

from .base import BaseDriver, register_driver
from ..models import Host
from ..settings import settings


@register_driver("mikrotik")
class MikroTikDriver(BaseDriver):
    """Driver for MikroTik devices using the REST API available in RouterOS 7."""

    type = "mikrotik"

    async def supported_actions(self) -> Dict[str, str]:
        return {
            "RECARGAR_SALDO": "Recargar saldo a la tarjeta SIM",
            "CONSULTAR_SALDO": "Consultar saldo actual de la SIM",
            "VER_LOGS_USSD": "Ver registros de USSD relacionados",
        }

    async def execute(self, action_key: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute one of the supported actions on the MikroTik router.

        The following action keys are recognised:

        - ``CONSULTAR_SALDO``: send a USSD command ``*222#`` to query the SIM
          balance.  No parameters are required.
        - ``RECARGAR_SALDO``: send a USSD command provided via ``params['code']``
          or ``params['pin']`` to top up the SIM.  If no code is supplied, a
          ``ValueError`` is raised.
        - ``VER_LOGS_USSD``: fetch the router log and return only the entries
          related to USSD commands.
        
        The return value is a dictionary with at least ``raw`` (string or
        serialisable object) and ``parsed`` (structured representation) keys.
        """
        params = params or {}
        supported = await self.supported_actions()
        if action_key not in supported:
            raise ValueError(f"Action '{action_key}' not supported by MikroTik driver")

        # Build auth header once
        headers = {"Authorization": self._build_auth_header()}

        async with self._get_client() as client:
            if action_key == "CONSULTAR_SALDO":
                # Send USSD request to check balance
                payload = {"command": "USSD", "number": "*222#"}
                url = f"{self.base_url}/rest/tool/sms/send"
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                raw = resp.text
                parsed = {"message": raw}
                return {"raw": raw, "parsed": parsed}

            if action_key == "RECARGAR_SALDO":
                # Require a code in params; no default fallback
                code = params.get("code") or params.get("pin")
                if not code:
                    raise ValueError("'RECARGAR_SALDO' requires 'code' or 'pin' parameter")
                payload = {"command": "USSD", "number": str(code)}
                url = f"{self.base_url}/rest/tool/sms/send"
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                raw = resp.text
                parsed = {"message": raw}
                return {"raw": raw, "parsed": parsed}

            if action_key == "VER_LOGS_USSD":
                # Retrieve logs and filter USSD messages
                url = f"{self.base_url}/rest/log"
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                logs = resp.json()
                # logs may be a list of log entries; filter lines containing 'USSD'
                # Perform json.dumps on each entry to catch nested structures
                ussd_logs = [entry for entry in logs if "USSD" in json.dumps(entry, ensure_ascii=False)]
                raw = json.dumps(logs, ensure_ascii=False, default=str)
                return {"raw": raw, "parsed": ussd_logs}

            # Should never reach here due to supported_actions check
            raise NotImplementedError(action_key)

    def _build_auth_header(self) -> str:
        token = f"{self.host.username}:{self.host.password}"
        b64 = base64.b64encode(token.encode()).decode()
        return f"Basic {b64}"

    async def health_check(self) -> Tuple[Optional[float], Optional[str]]:
        """Perform a health check against the MikroTik router.

        Returns a tuple ``(latency_ms, error)``.  If the request succeeds,
        ``error`` is ``None``.  On failure, ``latency_ms`` will be ``None``
        and ``error`` contains a string description.  This format allows
        upstream code to derive ``online`` status as ``error is None``.
        """
        url = f"{self.base_url}/rest/system/resource"
        headers = {"Authorization": self._build_auth_header()}
        try:
            async with self._get_client() as client:
                # Measure latency using a high‑precision counter.  We import
                # ``time`` here to avoid adding a top‑level import just for
                # this method.
                import time  # local import to prevent unused import warnings

                start = time.perf_counter()
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                end = time.perf_counter()
                latency_ms = (end - start) * 1000.0
                return (latency_ms, None)
        except Exception as exc:
            return (None, str(exc))