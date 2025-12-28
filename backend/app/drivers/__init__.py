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
from .tplink_openwrt_ssh import TPLinkOpenWrtSSHDriver
from ..models import RouterType


_DRIVER_REGISTRY: Dict[str, Type[RouterDriver]] = {
    RouterType.MIKROTIK_ROUTEROS_REST.value: MikroTikRouterOSRestDriver,
    RouterType.TP_LINK_OPENWRT_SSH.value: TPLinkOpenWrtSSHDriver,
}


def get_driver(router_type: str):
    if not router_type:
        raise KeyError("router_type is empty")

    raw = str(router_type).strip()
    key = raw.upper()

    aliases = {
        # Mikrotik
        "MIKROTIK": RouterType.MIKROTIK_ROUTEROS_REST.value,
        "MIKROTIK_REST": RouterType.MIKROTIK_ROUTEROS_REST.value,
        "MIKROTIK_ROUTEROS": RouterType.MIKROTIK_ROUTEROS_REST.value,
        "MIKROTIK_ROUTEROS_REST": RouterType.MIKROTIK_ROUTEROS_REST.value,

        # TP-Link / OpenWrt
        "TPLINK": RouterType.TP_LINK_OPENWRT_SSH.value,
        "TP-LINK": RouterType.TP_LINK_OPENWRT_SSH.value,
        "OPENWRT": RouterType.TP_LINK_OPENWRT_SSH.value,
        "TP_LINK_OPENWRT_SSH": RouterType.TP_LINK_OPENWRT_SSH.value,
        "TP-LINK_OPENWRT_SSH": RouterType.TP_LINK_OPENWRT_SSH.value,
    }

    key = aliases.get(key, key)

    try:
        cls = _DRIVER_REGISTRY[key]
    except KeyError:
        available = ", ".join(sorted(_DRIVER_REGISTRY.keys()))
        raise KeyError(
            f"Unknown router_type '{router_type}'. Normalized '{key}'. Available: {available}"
        )

    return cls()
