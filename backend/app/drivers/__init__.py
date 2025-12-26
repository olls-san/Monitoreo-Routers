"""Router drivers package.

Drivers encapsulate the details of communicating with various
router types. The application does not hardcode any commands
outside of the drivers; it simply asks a driver to execute an
action identified by an ``action_key``. Each driver exposes
``execute_action()``, ``list_supported_actions()`` and
``validate()``.
"""

from __future__ import annotations

from typing import Dict, Type

from .base import RouterDriver
from .mikrotik_rest import MikroTikRouterOSRestDriver
from ..models import RouterType


_DRIVER_REGISTRY: Dict[str, Type[RouterDriver]] = {
    RouterType.MIKROTIK_ROUTEROS_REST.value: MikroTikRouterOSRestDriver,
}


def get_driver(router_type: str):
    if not router_type:
        raise KeyError("router_type is empty")

    raw = str(router_type).strip()

    # 1) normalización básica
    key = raw.upper()

    # 2) aliases soportados (valores “humanos” o legacy en DB)
    aliases = {
        "MIKROTIK": "MIKROTIK_ROUTEROS_REST",
        "MIKROTIK_REST": "MIKROTIK_ROUTEROS_REST",
        "MIKROTIK_ROUTEROS": "MIKROTIK_ROUTEROS_REST",
        "MIKROTIK_ROUTEROS_REST": "MIKROTIK_ROUTEROS_REST",

        # caso exacto del error del log:
        "MIKROTIK".lower(): "MIKROTIK_ROUTEROS_REST",  # "mikrotik"
    }

    # si vino "mikrotik" (lower) u otro alias, mapear
    if raw in aliases:
        key = aliases[raw]
    elif key in aliases:
        key = aliases[key]

    # 3) lookup final
    try:
        cls = _DRIVER_REGISTRY[key]
    except KeyError:
        available = ", ".join(sorted(_DRIVER_REGISTRY.keys()))
        raise KeyError(f"Unknown router_type '{router_type}'. Normalized '{key}'. Available: {available}")

    return cls()
