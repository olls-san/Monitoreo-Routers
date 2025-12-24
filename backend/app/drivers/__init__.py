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


def get_driver(router_type: str) -> RouterDriver:
    """Return a driver instance for the given router type.

    Raises:
        KeyError: if no driver is registered for the type.
    """
    cls = _DRIVER_REGISTRY[router_type]
    return cls()
