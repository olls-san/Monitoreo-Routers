"""Driver for MikroTik RouterOS using its REST API.

This driver communicates with RouterOS's HTTP API, authenticating
via basic authentication. Only a small subset of the API is used
for the supported actions.

Warning: the driver uses basic authentication over HTTP. When
deploying in production you should enable HTTPS on your routers
and use a proper certificate.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List

import httpx

from ..models import Host
from .base import RouterDriver
from ..services.logs_parser import parse_ussd_logs

logger = logging.getLogger(__name__)


class MikroTikRouterOSRestDriver(RouterDriver):
    """Concrete driver for MikroTik RouterOS via REST API."""

    # Stable action keys supported by this driver
    ACTION_RECARGAR_SALDO = "RECARGAR_SALDO"
    ACTION_CONSULTAR_SALDO = "CONSULTAR_SALDO"
    ACTION_VER_LOGS_USSD = "VER_LOGS_USSD"

    def list_supported_actions(self) -> List[str]:
        return [
            self.ACTION_RECARGAR_SALDO,
            self.ACTION_CONSULTAR_SALDO,
            self.ACTION_VER_LOGS_USSD,
        ]

    @asynccontextmanager
    async def _get_client(self, host: Host):
        """Yield an HTTP client configured for the given host and close it safely."""
        base_url = f"http://{host.ip}:{host.port}/rest"
        auth = (host.username, host.password) if (host.username or host.password) else None

        client = httpx.AsyncClient(
            base_url=base_url,
            auth=auth,
            timeout=30.0,
        )
        try:
            yield client
        finally:
            await client.aclose()

    async def execute_action(self, host: Host, action_key: str, **kwargs: Any) -> Dict[str, Any]:
        """Execute an action on a MikroTik router.

        Returns a dictionary with keys ``raw`` and optionally ``parsed``.
        Raises an exception if the request fails.
        """
        async with self._get_client(host) as client:
            if action_key == self.ACTION_RECARGAR_SALDO:
                payload = {
                    "port": "lte1",
                    "phone-number": "*133*1*4*4*1#",
                    "message": "",
                    "type": "ussd",
                }
                response = await client.post("/tool/sms/send", json=payload)
                response.raise_for_status()
                return {"raw": response.json()}

            if action_key == self.ACTION_CONSULTAR_SALDO:
                payload = {
                    "port": "lte1",
                    "phone-number": "*222*328#",
                    "message": "",
                    "type": "ussd",
                }
                response = await client.post("/tool/sms/send", json=payload)
                response.raise_for_status()
                return {"raw": response.json()}

            if action_key == self.ACTION_VER_LOGS_USSD:
                # Fetch logs and filter messages containing 'ussd' (case-insensitive).
                response = await client.get("/log")
                response.raise_for_status()
                logs = response.json()  # RouterOS returns a JSON array of log records

                ussd_logs = [
                    entry
                    for entry in logs
                    if isinstance(entry, dict)
                    and isinstance(entry.get("message"), str)
                    and "ussd" in entry["message"].lower()
                ]

                parsed = parse_ussd_logs(ussd_logs)
                return {"raw": logs, "parsed": parsed}

            raise ValueError(f"Unsupported action '{action_key}' for MikroTik driver")

    async def validate(self, host: Host) -> None:
        """Validate connectivity to the router.

        A lightweight GET request is performed against the system resource
        endpoint. If this request fails an exception is raised.
        """
        async with self._get_client(host) as client:
            response = await client.get("/system/resource")
            response.raise_for_status()

        logger.debug("Host %s validated successfully", host)
