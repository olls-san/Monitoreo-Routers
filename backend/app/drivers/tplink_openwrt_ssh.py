"""TP-Link (OpenWrt) driver over SSH.

- Health check: simple ping (online/offline).
- Balance/data check: read USSD status from syslog (logread -e USSD).
  We DO NOT execute USSD from MoniTe to avoid modem port conflicts.
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import RouterDriver
from ..models import Host


# Example log lines:
# Sat Dec 27 07:00:30 2025 user.notice USSD: Recarga efectuafa: Tarifa: Activa. Datos: 7.53 GB validos 20 dias. Saldo: 319.23
SYSLOG_DT_RE = re.compile(r"^(?P<wday>\w{3})\s+(?P<mon>\w{3})\s+(?P<day>\d{1,2})\s+(?P<time>\d{2}:\d{2}:\d{2})\s+(?P<year>\d{4})\s+(?P<rest>.*)$")
USSD_PARSE_RE = re.compile(
    r"Datos:\s*(?P<datos>[\d.]+)\s*(?P<unit>GB|MB)\s+validos\s+(?P<dias>\d+)\s+dias\.\s+Saldo:\s*(?P<saldo>[\d.]+)",
    re.IGNORECASE,
)


class TPLinkOpenWrtSSHDriver(RouterDriver):
    """Driver for OpenWrt routers accessible via SSH."""

    # Action keys (stable)
    ACTION_CONSULTAR_SALDO = "CONSULTAR_SALDO"
    ACTION_VER_LOGS_USSD = "VER_LOGS_USSD"

    def list_supported_actions(self) -> List[str]:
        return [
            self.ACTION_CONSULTAR_SALDO,
            self.ACTION_VER_LOGS_USSD,
        ]

    async def validate(self, host: Host) -> None:
        """Online/offline via ping (simple, no credentials)."""
        # -c 1: one packet
        # -W 1: timeout 1s (busybox ping uses -W seconds)
        proc = await asyncio.create_subprocess_exec(
            "ping",
            "-c",
            "1",
            "-W",
            "1",
            host.ip,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        rc = await proc.wait()
        if rc != 0:
            raise RuntimeError("Ping failed")

    async def execute_action(self, host: Host, action_key: str, **kwargs: Any) -> Dict[str, Any]:
        if action_key == self.ACTION_CONSULTAR_SALDO:
            # Read last USSD line from syslog
            line = await self._ssh(host, "sh -c 'logread -e USSD | tail -n 1'")
            parsed = self._parse_ussd_line(line)
            return {"raw": line, "parsed": parsed}

        if action_key == self.ACTION_VER_LOGS_USSD:
            n = int(kwargs.get("lines", 20))
            raw_text = await self._ssh(host, f"sh -c 'logread -e USSD | tail -n {n}'")
            lines = [ln for ln in raw_text.splitlines() if ln.strip()]
            items = [self._as_log_item(ln) for ln in lines]
            return {"raw": items, "parsed": {"count": len(items)}}

        raise ValueError(f"Action '{action_key}' not supported by TP-Link/OpenWrt driver")

    # -----------------------
    # Internals
    # -----------------------

    async def _ssh(self, host: Host, remote_cmd: str) -> str:
        """Run SSH command on router and return stdout."""
        user = host.username or "root"
        port = int(host.port or 22)

        proc = await asyncio.create_subprocess_exec(
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "ConnectTimeout=5",
            "-p",
            str(port),
            f"{user}@{host.ip}",
            remote_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        out, err = await proc.communicate()
        if proc.returncode != 0:
            msg = (err or out).decode(errors="ignore").strip()
            raise RuntimeError(msg or f"SSH failed with code {proc.returncode}")
        return out.decode(errors="ignore").strip()

    def _as_log_item(self, line: str) -> Dict[str, Any]:
        """Convert syslog line to {'time': 'YYYY-MM-DD HH:MM:SS', 'message': 'USSD: ...'}."""
        m = SYSLOG_DT_RE.match(line.strip())
        if not m:
            return {"time": None, "message": line.strip()}

        dt_str = f"{m.group('wday')} {m.group('mon')} {m.group('day')} {m.group('time')} {m.group('year')}"
        dt_iso = None
        try:
            # Example: "Sat Dec 27 07:00:30 2025"
            dt = datetime.strptime(dt_str, "%a %b %d %H:%M:%S %Y")
            dt_iso = dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            dt_iso = None

        rest = m.group("rest").strip()
        # We want message to start with "USSD:" if present
        idx = rest.find("USSD:")
        msg = rest[idx:] if idx != -1 else rest
        return {"time": dt_iso, "message": msg}

    def _parse_ussd_line(self, line: str) -> Dict[str, Any]:
        """Parse saldo/datos/dias from the USSD syslog line."""
        item = self._as_log_item(line)
        msg = item.get("message") or ""

        m = USSD_PARSE_RE.search(msg)
        if not m:
            return {
                "time": item.get("time"),
                "message": msg,
                "saldo": None,
                "datos_mb": None,
                "validos_dias": None,
                "ok_parse": False,
            }

        datos = float(m.group("datos"))
        unit = m.group("unit").upper()
        dias = int(m.group("dias"))
        saldo = float(m.group("saldo"))

        datos_mb = datos * 1024 if unit == "GB" else datos

        return {
            "time": item.get("time"),
            "message": msg,
            "saldo": saldo,
            "datos_mb": datos_mb,
            "validos_dias": dias,
            "ok_parse": True,
        }
