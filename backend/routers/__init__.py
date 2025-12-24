"""Import API router modules for easy inclusion in FastAPI app."""

from . import hosts  # noqa: F401
from . import actions  # noqa: F401
from . import automation  # noqa: F401

__all__ = ["hosts", "actions", "automation"]