"""Driver abstractions for MoniTe Web.

The system uses a Strategy pattern to interact with different types of routers.
Each driver must implement a common set of methods defined on the
`BaseDriver` class. New router types can be added by subclassing
`BaseDriver` and registering the subclass under a unique type string in the
`driver_registry` mapping.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

import httpx

from ..models import Host
from ..settings import settings


class BaseDriver(ABC):
    """Abstract base class for router drivers."""

    type: str  # subclasses must define a unique type identifier

    def __init__(self, host: Host) -> None:
        self.host = host

    @property
    def base_url(self) -> str:
        """Construct the base URL for API calls to this host.

        In the new architecture hosts no longer persist a custom port.  The
        driver itself chooses the default port for its protocol.  For HTTP
        drivers (including MikroTik REST) this returns a plain ``http`` URL
        using only the IP address.  Subclasses may override this property
        if they need to support different schemes (e.g. HTTPS) or default
        ports.
        """
        return f"http://{self.host.ip}"

    @asynccontextmanager
    async def _get_client(self) -> Any:
        """Provide an `httpx.AsyncClient` configured for the host.

        Subclasses may override this if they need to customise authentication
        behaviour. Ensures that the client is properly closed after use.
        """
        client = httpx.AsyncClient(timeout=settings.request_timeout)
        try:
            yield client
        finally:
            await client.aclose()

    @abstractmethod
    async def supported_actions(self) -> Dict[str, str]:
        """Return a mapping of action keys to human friendly descriptions."""

    @abstractmethod
    async def execute(self, action_key: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute the given action on the host and return a parsed response.

        Implementations should return a dictionary containing at minimum a
        `raw` field with the raw response payload (string or nested structures)
        and optionally a `parsed` field with a cleaned-up version of the
        response. Any additional data may also be returned. Errors should be
        raised as exceptions to be handled by the caller.
        """

    async def health_check(self) -> Dict[str, Any]:
        """Perform a lightweight check to determine if the host is online.

        Drivers may override this method if they have a more appropriate
        endpoint to call. Returns a dictionary with keys `online` (bool),
        `latency_ms` (float) and optionally an `error` (str) if offline.
        """
        try:
            async with self._get_client() as client:
                url = f"{self.base_url}/health"
                resp = await client.get(url)
                resp.raise_for_status()
                return {"online": True, "latency_ms": resp.elapsed.total_seconds() * 1000}
        except Exception as exc:
            return {"online": False, "latency_ms": None, "error": str(exc)}


# Global registry mapping a lower-case driver type to its class.  Drivers
# should register themselves via the ``register_driver`` decorator defined
# below.  Using a lower-case key avoids issues with case sensitivity on
# host.type values stored in the database.
driver_registry: Dict[str, type[BaseDriver]] = {}


def register_driver(arg=None):
    """Decorator to register a driver class under a specific type.

    This decorator can be used in two ways:

    1. Without arguments: ``@register_driver``.  In this form the
       decorated class **must** define a ``type`` class attribute.  The
       value of ``type`` (lower‑cased) will be used as the registry key.

    2. With a string argument: ``@register_driver("mikrotik")``.  In this
       form the argument specifies the type under which to register the
       class.  The class's own ``type`` attribute is ignored.

    In both cases, the resulting driver class is returned unmodified.  If
    called incorrectly (for example, without a type on the class), a
    ``ValueError`` is raised at decoration time.
    """
    # Case 1: decorator used without arguments (arg is actually the class)
    if arg and isinstance(arg, type):
        cls = arg
        # Determine the key from the class attribute
        type_key = getattr(cls, "type", None)
        if not type_key:
            raise ValueError(
                f"Driver class {cls.__name__} must define a class attribute 'type' when using @register_driver"
            )
        driver_registry[str(type_key).lower()] = cls
        return cls

    # Case 2: decorator used with a type string
    def decorator(cls: type[BaseDriver]):
        nonlocal arg  # the provided type string
        type_key = arg or getattr(cls, "type", None)
        if not type_key:
            raise ValueError(
                f"Driver class {cls.__name__} must define a class attribute 'type' or provide a type to @register_driver"
            )
        driver_registry[str(type_key).lower()] = cls
        return cls

    return decorator


def get_driver(host: Host) -> BaseDriver:
    """Instantiate the appropriate driver for the given host.

    Lookup is performed against the lower‑cased ``host.type``.  If no
    matching driver is registered, a ``ValueError`` is raised.
    """
    type_key = (host.type or "").strip().lower()
    cls = driver_registry.get(type_key)
    if not cls:
        raise ValueError(f"No driver registered for host type '{host.type}'")
    return cls(host)


# Attempt to import built-in drivers so that their decorators run and
# populate the registry.  If the import fails (for example, missing
# optional dependencies), we silently ignore the error; missing drivers
# will simply result in a ``ValueError`` when looked up.
try:
    from . import mikrotik  # noqa: F401
except Exception:
    # Do not crash the app if the driver cannot be imported (e.g., missing
    # dependencies).  Any attempt to use the unregistered driver will
    # produce a clear error via ``get_driver``.
    pass