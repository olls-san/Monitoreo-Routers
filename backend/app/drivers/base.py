"""Abstract base class for all router drivers.

Drivers must implement the three core methods defined here. The
rest of the application interacts with routers exclusively via
this interface, enabling easy addition of new router types in
the future without touching unrelated code.
"""

from __future__ import annotations

import abc
from typing import Any, Dict, List, Optional

from ..models import Host


class RouterDriver(abc.ABC):
    """Base class for router drivers.

    Concrete implementations must provide methods for executing
    actions, listing the supported actions, and validating a
    host configuration.
    """

    @abc.abstractmethod
    async def execute_action(self, host: Host, action_key: str, **kwargs: Any) -> Dict[str, Any]:
        """Execute a named action on the given host.

        Args:
            host: The Host instance containing connection details.
            action_key: A stable identifier representing the action
                to perform (e.g. ``"CONSULTAR_SALDO"``).
            **kwargs: Optional keyword arguments specific to the
                action.

        Returns:
            A dictionary representing both the raw response and
            structured parsed data. The dictionary MUST contain a
            ``raw`` key holding the raw response (as returned by the
            router) and MAY contain a ``parsed`` key with
            structured data extracted from the response.

        Raises:
            Exception: If the execution fails. Implementations
            should raise exceptions to signal failure so that
            upstream callers can record error information.
        """

    @abc.abstractmethod
    def list_supported_actions(self) -> List[str]:
        """Return a list of supported action keys.

        The frontend uses this information to show only the actions
        applicable to a given router type.
        """

    @abc.abstractmethod
    async def validate(self, host: Host) -> None:
        """Validate that a host is reachable and credentials are valid.

        Implementations should perform a lightweight operation
        (such as fetching a system resource) to ensure the router
        is accessible. Raise an exception if validation fails.
        """
