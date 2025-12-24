"""Deprecated MoniTe Web backend entrypoint.

This module previously served as the FastAPI entry point for the
MoniTe Web backend.  The project has been restructured so that all
active development happens under ``backend/app``.  To start the
application you should now run:

    uvicorn monite_web.backend.app.main:app --reload

This file is kept for backwards compatibility but will raise a
``RuntimeError`` if used directly to prevent accidental usage of the
outdated API implementation.
"""

from __future__ import annotations

import logging

import logging


# Immediately raise an error to prevent using this deprecated module as the
# application entrypoint.  Encourage users to switch to the new entry
# point under ``backend/app``.
raise RuntimeError(
    "The old backend entrypoint (monite_web.backend.main) is deprecated. "
    "Please run 'uvicorn monite_web.backend.app.main:app --reload' instead."
)